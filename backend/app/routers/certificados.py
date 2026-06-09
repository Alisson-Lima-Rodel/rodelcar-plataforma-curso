import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.ratelimit import limiter
from app.dependencies import get_current_aluno
from app.models import Aluno, Aula, Certificado, Matricula, Modulo, Progresso
from app.schemas.certificados import CertificadoResponse, CertificadoVerificacao

router = APIRouter(prefix="/certificados", tags=["certificados"])


@router.post("/{matricula_id}", response_model=CertificadoResponse, status_code=201)
async def emitir_certificado(
    matricula_id: uuid.UUID,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    matricula = (
        await db.execute(select(Matricula).where(Matricula.id == matricula_id))
    ).scalar_one_or_none()

    if matricula is None or matricula.aluno_id != aluno.id:
        raise HTTPException(
            status_code=404,
            detail={"error": {
                "code": "MATRICULA_NAO_ENCONTRADA",
                "message": "Matrícula não encontrada.",
                "details": None,
            }},
        )

    # Idempotência: já existe certificado?
    existing = (
        await db.execute(
            select(Certificado).where(Certificado.matricula_id == matricula.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "CERTIFICADO_JA_EMITIDO",
                "message": "Certificado já emitido para esta matrícula.",
                "details": None,
            }},
        )

    # Verifica conclusão: todas as aulas do curso devem estar concluídas
    total_aulas = await db.scalar(
        select(func.count(Aula.id))
        .join(Modulo, Aula.modulo_id == Modulo.id)
        .where(Modulo.curso_id == matricula.curso_id)
    ) or 0

    concluidas = await db.scalar(
        select(func.count(Progresso.id)).where(
            Progresso.matricula_id == matricula.id,
            Progresso.concluida.is_(True),
        )
    ) or 0

    if total_aulas == 0 or concluidas < total_aulas:
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "CURSO_NAO_CONCLUIDO",
                "message": (
                    f"Curso não concluído ({concluidas}/{total_aulas} aulas concluídas)."
                ),
                "details": None,
            }},
        )

    # Código não enumerável: token de 64 bits evita varredura do endpoint público
    # de verificação (que expõe nome do titular).
    ano = datetime.now(timezone.utc).year
    codigo = f"RC-{ano}-{secrets.token_hex(8).upper()}"

    cert = Certificado(matricula_id=matricula.id, codigo_verificacao=codigo)
    db.add(cert)
    await db.commit()
    await db.refresh(cert)

    return CertificadoResponse(
        id=cert.id,
        codigo_verificacao=cert.codigo_verificacao,
        emitido_em=cert.emitido_em,
    )


@router.get("/{codigo}/verificar", response_model=CertificadoVerificacao)
@limiter.limit("20/minute")
async def verificar_certificado(
    request: Request, codigo: str, db: AsyncSession = Depends(get_db)
):
    cert = (
        await db.execute(
            select(Certificado)
            .where(Certificado.codigo_verificacao == codigo)
            .options(
                selectinload(Certificado.matricula).options(
                    selectinload(Matricula.aluno),
                    selectinload(Matricula.curso),
                )
            )
        )
    ).scalar_one_or_none()

    if cert is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {
                "code": "CERTIFICADO_NAO_ENCONTRADO",
                "message": "Certificado não encontrado.",
                "details": None,
            }},
        )

    return CertificadoVerificacao(
        valido=True,
        aluno_nome=cert.matricula.aluno.nome,
        curso=cert.matricula.curso.titulo,
        emitido_em=cert.emitido_em,
    )

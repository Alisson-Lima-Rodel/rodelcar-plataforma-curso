import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.certificado_pdf import gerar_pdf_certificado
from app.core.config import settings
from app.core.db import get_db
from app.core.email_transacional import email_certificado
from app.core.notificacoes import enviar_email_bruto, enviar_whatsapp_texto
from app.core.ratelimit import limiter
from app.dependencies import get_current_aluno
from app.models import (
    Aluno, Aula, Certificado, Curso, Matricula, Modulo, Progresso, Quiz,
    StatusMatricula, TentativaQuiz,
)
from app.schemas.certificados import (
    CertificadoEnvioResponse,
    CertificadoResponse,
    CertificadoVerificacao,
)

router = APIRouter(prefix="/certificados", tags=["certificados"])


def _erro(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


async def _carregar_certificado_do_aluno(
    matricula_id: uuid.UUID, aluno: Aluno, db: AsyncSession
) -> tuple[Certificado, Matricula, Curso]:
    """Carrega o certificado emitido de uma matrícula DO aluno logado (ou 404)."""
    matricula = (
        await db.execute(
            select(Matricula)
            .where(Matricula.id == matricula_id)
            .options(selectinload(Matricula.curso))
        )
    ).scalar_one_or_none()
    if matricula is None or matricula.aluno_id != aluno.id:
        raise _erro(404, "MATRICULA_NAO_ENCONTRADA", "Matrícula não encontrada.")

    cert = (
        await db.execute(
            select(Certificado).where(Certificado.matricula_id == matricula.id)
        )
    ).scalar_one_or_none()
    if cert is None:
        raise _erro(404, "CERTIFICADO_NAO_EMITIDO", "Certificado ainda não emitido.")
    return cert, matricula, matricula.curso


def _verify_url(codigo: str) -> str:
    return f"{settings.PORTAL_URL.rstrip('/')}/verificar/{codigo}"


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

    # Vigência: certificado é prova de conclusão COM acesso legítimo. Matrícula
    # revogada/expirada (ex.: reembolso) não emite — senão um aluno estornado
    # geraria prova de conclusão falsa.
    if matricula.status != StatusMatricula.ativo:
        raise _erro(
            409, "MATRICULA_NAO_ATIVA",
            "Matrícula não está ativa — certificado indisponível.",
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

    # Gate de quiz: todo módulo do curso com quiz ATIVO precisa de uma tentativa
    # aprovada nesta matrícula (assistir não basta; o aluno tem de PASSAR).
    quizzes_ativos = set(
        (
            await db.execute(
                select(Quiz.id)
                .join(Modulo, Quiz.modulo_id == Modulo.id)
                .where(Modulo.curso_id == matricula.curso_id, Quiz.ativo.is_(True))
            )
        ).scalars().all()
    )
    if quizzes_ativos:
        aprovados = set(
            (
                await db.execute(
                    select(TentativaQuiz.quiz_id)
                    .where(
                        TentativaQuiz.matricula_id == matricula.id,
                        TentativaQuiz.quiz_id.in_(quizzes_ativos),
                        TentativaQuiz.aprovado.is_(True),
                    )
                    .distinct()
                )
            ).scalars().all()
        )
        if aprovados != quizzes_ativos:
            raise _erro(
                409, "QUIZ_PENDENTE",
                f"Você precisa passar em todos os quizzes "
                f"({len(aprovados)}/{len(quizzes_ativos)} concluídos).",
            )

    # Código não enumerável: token de 64 bits evita varredura do endpoint público
    # de verificação (que expõe nome do titular).
    ano = datetime.now(timezone.utc).year
    codigo = f"RC-{ano}-{secrets.token_hex(8).upper()}"

    cert = Certificado(matricula_id=matricula.id, codigo_verificacao=codigo)
    db.add(cert)
    await db.commit()
    await db.refresh(cert)

    # E-mail do certificado (best-effort, fora da transação). Emissão é única por
    # matrícula (idempotência via unique), então não há e-mail duplicado.
    curso = await db.get(Curso, matricula.curso_id)
    if aluno.email:
        assunto, corpo = email_certificado(
            aluno.nome,
            curso.titulo if curso else "seu curso",
            _verify_url(cert.codigo_verificacao),
        )
        await enviar_email_bruto(aluno.email, assunto, corpo, log_ref=str(aluno.id))

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


@router.get("/{matricula_id}/pdf")
async def baixar_certificado_pdf(
    matricula_id: uuid.UUID,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """PDF do certificado (do próprio aluno). Gerado on-the-fly com reportlab."""
    cert, _matricula, curso = await _carregar_certificado_do_aluno(
        matricula_id, aluno, db
    )
    pdf = gerar_pdf_certificado(
        aluno_nome=aluno.nome,
        curso_titulo=curso.titulo,
        codigo=cert.codigo_verificacao,
        emitido_em=cert.emitido_em,
        horas=curso.horas,
        verify_url=_verify_url(cert.codigo_verificacao),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="certificado-{cert.codigo_verificacao}.pdf"'
            )
        },
    )


@router.post("/{matricula_id}/enviar-whatsapp", response_model=CertificadoEnvioResponse)
@limiter.limit("6/minute")
async def enviar_certificado_whatsapp(
    request: Request,
    matricula_id: uuid.UUID,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Envia o link público de verificação do certificado pelo WhatsApp do aluno."""
    cert, _matricula, curso = await _carregar_certificado_do_aluno(
        matricula_id, aluno, db
    )
    if not aluno.telefone:
        raise _erro(
            422,
            "TELEFONE_AUSENTE",
            "Cadastre um telefone no seu perfil para receber por WhatsApp.",
        )

    primeiro_nome = aluno.nome.split()[0] if aluno.nome else "aluno(a)"
    texto = (
        f"🎓 Olá {primeiro_nome}! Seu certificado de conclusão do curso "
        f"*{curso.titulo}* na RödelCar está pronto.\n\n"
        f"Verifique a autenticidade aqui:\n{_verify_url(cert.codigo_verificacao)}"
    )
    msg_id = await enviar_whatsapp_texto(
        aluno.telefone, texto, log_ref=str(aluno.id)
    )
    return CertificadoEnvioResponse(enviado=msg_id is not None)

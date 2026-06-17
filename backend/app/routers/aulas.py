import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import panda
from app.core.config import settings
from app.core.db import get_db
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.models import Aluno, Aula, Matricula, Modulo, Progresso, StatusMatricula
from app.schemas.aulas import AulaDetail, MaterialResumo, ProgressoAula

router = APIRouter(prefix="/aulas", tags=["aulas"])


@router.get("/{aula_id}", response_model=AulaDetail)
async def obter_aula(
    aula_id: uuid.UUID,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    aula = (
        await db.execute(
            select(Aula)
            .where(Aula.id == aula_id)
            .options(selectinload(Aula.materiais), selectinload(Aula.modulo))
        )
    ).scalar_one_or_none()

    if aula is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {
                "code": "AULA_NAO_ENCONTRADA",
                "message": "Aula não encontrada.",
                "details": None,
            }},
        )

    curso_id = aula.modulo.curso_id
    await checar_vigencia_aluno(aluno.id, db)

    matricula = (
        await db.execute(
            select(Matricula).where(
                Matricula.aluno_id == aluno.id,
                Matricula.curso_id == curso_id,
                Matricula.status == StatusMatricula.ativo,
            )
        )
    ).scalar_one_or_none()

    if matricula is None:
        any_status = (
            await db.execute(
                select(Matricula.status).where(
                    Matricula.aluno_id == aluno.id,
                    Matricula.curso_id == curso_id,
                )
            )
        ).scalar_one_or_none()

        if any_status is not None:
            raise HTTPException(
                status_code=403,
                detail={"error": {
                    "code": "MATRICULA_EXPIRADA",
                    "message": "Sua matrícula neste curso expirou ou foi bloqueada.",
                    "details": None,
                }},
            )
        raise HTTPException(
            status_code=403,
            detail={"error": {
                "code": "ACESSO_NEGADO",
                "message": "Você não possui matrícula neste curso.",
                "details": None,
            }},
        )

    progresso = (
        await db.execute(
            select(Progresso).where(
                Progresso.matricula_id == matricula.id,
                Progresso.aula_id == aula_id,
            )
        )
    ).scalar_one_or_none()

    # Token DRM por sessão (None se DRM desligado → embed público).
    token = panda.assinar_drm_token()

    return AulaDetail(
        id=aula.id,
        titulo=aula.titulo,
        modulo_id=aula.modulo_id,
        panda_video_id=aula.panda_video_id,
        duracao_segundos=aula.duracao_segundos,
        materiais=[
            MaterialResumo(id=m.id, nome=m.nome, url_pdf=m.url_pdf)
            for m in aula.materiais
        ],
        progresso=ProgressoAula(
            concluida=progresso.concluida if progresso else False,
            percentual=float(progresso.percentual) if progresso else 0.0,
            posicao_segundos=progresso.posicao_segundos if progresso else 0,
        ),
        player_token=token,
        drm_group_id=settings.PANDA_DRM_GROUP_ID if token else None,
    )

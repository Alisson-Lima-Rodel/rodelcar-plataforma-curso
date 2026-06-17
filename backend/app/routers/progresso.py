import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.models import Aluno, Aula, Matricula, Modulo, Progresso, StatusMatricula
from app.schemas.progresso import ProgressoRequest, ProgressoResponse

router = APIRouter(prefix="/progresso", tags=["progresso"])


@router.post("", response_model=ProgressoResponse)
async def salvar_progresso(
    body: ProgressoRequest,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    aula = (
        await db.execute(
            select(Aula)
            .where(Aula.id == body.aula_id)
            .options(selectinload(Aula.modulo))
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
        code = "MATRICULA_EXPIRADA" if any_status is not None else "ACESSO_NEGADO"
        raise HTTPException(
            status_code=403,
            detail={"error": {
                "code": code,
                "message": "Acesso ao conteúdo não permitido.",
                "details": None,
            }},
        )

    # Tempo real desde o último ping desta linha, limitado a 30s (~2x o intervalo
    # de ping) para não creditar pausas/abas em segundo plano. Referencia a linha
    # EXISTENTE (Progresso.atualizado_em) dentro do DO UPDATE — não o EXCLUDED.
    delta_assistido = func.least(
        func.extract("epoch", func.now() - Progresso.atualizado_em), 30
    )

    # Upsert idempotente: mesma (matricula, aula) → atualiza em vez de duplicar.
    # No INSERT puro `segundos_assistidos` nasce 0; só acumula no UPDATE (a 1ª
    # batida de uma aula nova não credita tempo — não há janela anterior).
    update_set = {
        "percentual": body.percentual,
        "concluida": body.concluida,
        "segundos_assistidos": (
            Progresso.segundos_assistidos + cast(delta_assistido, Integer)
        ),
        "atualizado_em": func.now(),
    }
    # Só mexe na posição quando o cliente a envia (player). O botão "Concluir" não
    # manda → preserva onde o aluno parou.
    if body.posicao_segundos is not None:
        update_set["posicao_segundos"] = body.posicao_segundos

    await db.execute(
        pg_insert(Progresso)
        .values(
            id=uuid.uuid4(),
            matricula_id=matricula.id,
            aula_id=body.aula_id,
            percentual=body.percentual,
            concluida=body.concluida,
            posicao_segundos=body.posicao_segundos or 0,
            segundos_assistidos=0,
        )
        .on_conflict_do_update(
            constraint="uq_matricula_aula",
            set_=update_set,
        )
    )
    await db.commit()

    # Recalcula % do curso: soma de todos os percentuais / total de aulas do curso
    total_aulas = await db.scalar(
        select(func.count(Aula.id))
        .join(Modulo, Aula.modulo_id == Modulo.id)
        .where(Modulo.curso_id == matricula.curso_id)
    ) or 0

    sum_pct = float(
        await db.scalar(
            select(func.coalesce(func.sum(Progresso.percentual), 0.0))
            .where(Progresso.matricula_id == matricula.id)
        ) or 0
    )

    curso_percentual = round(sum_pct / total_aulas, 1) if total_aulas > 0 else 0.0

    return ProgressoResponse(
        aula_id=body.aula_id,
        percentual=body.percentual,
        concluida=body.concluida,
        curso_percentual=curso_percentual,
        posicao_segundos=body.posicao_segundos or 0,
    )

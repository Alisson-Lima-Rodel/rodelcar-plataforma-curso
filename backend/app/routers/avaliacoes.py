"""Avaliações (reviews) de curso por alunos matriculados.

POST/GET sob `/cursos/{slug}/avaliacoes`. Só quem tem matrícula avalia (comprador
verificado). A média alimenta o `aggregateRating` do JSON-LD (estrelas no Google).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.dependencies import get_current_aluno
from app.models import Aluno, Avaliacao, Curso, Matricula, StatusCurso, StatusMatricula
from app.schemas.avaliacoes import (
    AvaliacaoCreate,
    AvaliacaoMinha,
    AvaliacaoPublica,
    AvaliacoesResponse,
)

router = APIRouter(prefix="/cursos", tags=["avaliacoes"])

_APROVADO = "Aprovado"


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


def _autor(nome: str | None) -> str:
    """Nome abreviado para exibição pública: 'João Silva' → 'João S.'."""
    partes = (nome or "").split()
    if not partes:
        return "Aluno(a)"
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1][0]}."


async def _curso_por_slug(slug: str, db: AsyncSession) -> Curso:
    # Curso inativo está fora do site: não mostra nem aceita avaliações (mesma
    # regra da vitrine/página de venda).
    curso = (
        await db.execute(
            select(Curso).where(
                Curso.slug == slug, Curso.status == StatusCurso.ativo
            )
        )
    ).scalar_one_or_none()
    if curso is None:
        raise _err(404, "CURSO_NAO_ENCONTRADO", "Curso não encontrado.")
    return curso


async def media_e_total(db: AsyncSession, curso_id: uuid.UUID) -> tuple[float | None, int]:
    """Média (1 casa) e contagem das avaliações aprovadas — reusado no JSON-LD."""
    media, total = (
        await db.execute(
            select(func.avg(Avaliacao.nota), func.count(Avaliacao.id))
            .join(Aluno, Avaliacao.aluno_id == Aluno.id)
            .where(
                Avaliacao.curso_id == curso_id,
                Avaliacao.status == _APROVADO,
                Aluno.bloqueado.is_(False),  # autor banido não conta na prova social
            )
        )
    ).one()
    return (round(float(media), 1) if media is not None else None, int(total or 0))


@router.get("/{slug}/avaliacoes", response_model=AvaliacoesResponse)
async def listar_avaliacoes(slug: str, db: AsyncSession = Depends(get_db)):
    curso = await _curso_por_slug(slug, db)
    rows = (
        await db.execute(
            select(Avaliacao, Aluno.nome)
            .join(Aluno, Avaliacao.aluno_id == Aluno.id)
            .where(
                Avaliacao.curso_id == curso.id,
                Avaliacao.status == _APROVADO,
                Aluno.bloqueado.is_(False),  # esconde review de autor banido
            )
            .order_by(Avaliacao.criado_em.desc())
            .limit(50)
        )
    ).all()
    items = [
        AvaliacaoPublica(
            autor=_autor(nome), nota=a.nota, texto=a.texto, criado_em=a.criado_em
        )
        for a, nome in rows
    ]
    media, total = await media_e_total(db, curso.id)
    return AvaliacoesResponse(items=items, media=media, total=total)


@router.get("/{slug}/avaliacoes/minha", response_model=AvaliacaoMinha | None)
async def minha_avaliacao(
    slug: str,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """A avaliação do próprio aluno (ou null) — preenche o formulário no LMS."""
    curso = await _curso_por_slug(slug, db)
    av = (
        await db.execute(
            select(Avaliacao).where(
                Avaliacao.aluno_id == aluno.id, Avaliacao.curso_id == curso.id
            )
        )
    ).scalar_one_or_none()
    if av is None:
        return None
    return AvaliacaoMinha(nota=av.nota, texto=av.texto, status=av.status)


@router.post("/{slug}/avaliacoes", response_model=AvaliacaoMinha)
async def avaliar_curso(
    slug: str,
    body: AvaliacaoCreate,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Cria/atualiza a avaliação do aluno. Exige matrícula ATIVA (comprador com
    acesso vigente) — espelha a checagem de /aulas e /progresso. Bloqueado/expirado
    não avalia (anti-fraude na prova social que vira aggregateRating)."""
    curso = await _curso_por_slug(slug, db)
    matricula_ativa = await db.scalar(
        select(Matricula.id).where(
            Matricula.aluno_id == aluno.id,
            Matricula.curso_id == curso.id,
            Matricula.status == StatusMatricula.ativo,
        )
    )
    if not matricula_ativa:
        raise _err(
            403, "PRECISA_MATRICULA", "Só quem tem o curso ativo pode avaliá-lo."
        )

    async def _carrega() -> Avaliacao | None:
        return (
            await db.execute(
                select(Avaliacao).where(
                    Avaliacao.aluno_id == aluno.id, Avaliacao.curso_id == curso.id
                )
            )
        ).scalar_one_or_none()

    av = await _carrega()
    if av is None:
        av = Avaliacao(
            aluno_id=aluno.id,
            curso_id=curso.id,
            nota=body.nota,
            texto=(body.texto or None),
        )
        db.add(av)
        try:
            await db.commit()
        except IntegrityError:
            # Corrida: dois POST simultâneos do mesmo (aluno, curso). O unique
            # garante 1 linha; aqui caímos no caminho de update em vez de 500.
            await db.rollback()
            av = await _carrega()
            if av is None:  # pragma: no cover (defensivo)
                raise _err(409, "AVALIACAO_CONFLITO", "Tente novamente.")
            av.nota = body.nota
            av.texto = body.texto or None
            await db.commit()
    else:
        # Re-avaliar atualiza nota/texto; o status (moderação) é preservado.
        av.nota = body.nota
        av.texto = body.texto or None
        await db.commit()
    await db.refresh(av)
    return AvaliacaoMinha(nota=av.nota, texto=av.texto, status=av.status)

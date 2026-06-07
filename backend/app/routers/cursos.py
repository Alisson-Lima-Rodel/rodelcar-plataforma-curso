from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Aula, Curso, Modulo, TipoCurso
from app.schemas.cursos import (
    CursoDetail,
    CursoListItem,
    CursoListResponse,
    ModuloResumo,
)

router = APIRouter(prefix="/cursos", tags=["cursos"])

# Tamanho máximo da prévia usada em `descricao_curta` na vitrine.
_DESCRICAO_CURTA_MAX = 160


def _descricao_curta(descricao: str | None) -> str | None:
    if not descricao:
        return None
    texto = descricao.strip()
    if len(texto) <= _DESCRICAO_CURTA_MAX:
        return texto
    return texto[: _DESCRICAO_CURTA_MAX - 1].rstrip() + "…"


@router.get("", response_model=CursoListResponse)
async def listar_cursos(
    tipo: TipoCurso | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Vitrine pública de cursos, com contagem de módulos e aulas."""
    total_modulos = (
        select(func.count(Modulo.id))
        .where(Modulo.curso_id == Curso.id)
        .correlate(Curso)
        .scalar_subquery()
    )
    total_aulas = (
        select(func.count(Aula.id))
        .select_from(Aula)
        .join(Modulo, Aula.modulo_id == Modulo.id)
        .where(Modulo.curso_id == Curso.id)
        .correlate(Curso)
        .scalar_subquery()
    )

    base = select(Curso)
    count_stmt = select(func.count(Curso.id))
    if tipo is not None:
        base = base.where(Curso.tipo == tipo)
        count_stmt = count_stmt.where(Curso.tipo == tipo)

    total = await db.scalar(count_stmt) or 0

    stmt = (
        base.add_columns(
            total_modulos.label("total_modulos"),
            total_aulas.label("total_aulas"),
        )
        .order_by(Curso.destaque.desc(), Curso.titulo)
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).all()

    items = [
        CursoListItem(
            id=curso.id,
            slug=curso.slug,
            titulo=curso.titulo,
            descricao_curta=_descricao_curta(curso.descricao),
            tipo=curso.tipo,
            preco=curso.preco,
            validade_dias=curso.validade_dias,
            thumbnail_url=curso.thumbnail_url,
            total_modulos=n_modulos,
            total_aulas=n_aulas,
            destaque=curso.destaque,
        )
        for curso, n_modulos, n_aulas in rows
    ]
    return CursoListResponse(items=items, total=total, page=page, size=size)


@router.get("/{slug}", response_model=CursoDetail)
async def obter_curso(slug: str, db: AsyncSession = Depends(get_db)):
    """Detalhe da página de venda, com a estrutura de módulos e aulas."""
    curso = (
        await db.execute(select(Curso).where(Curso.slug == slug))
    ).scalar_one_or_none()

    if curso is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {
                "code": "CURSO_NAO_ENCONTRADO",
                "message": "Curso não encontrado.",
                "details": None,
            }},
        )

    # Conta aulas por módulo no banco — não carrega as linhas de aula
    # (evita exaustão de memória neste endpoint público).
    total_aulas = (
        select(func.count(Aula.id))
        .where(Aula.modulo_id == Modulo.id)
        .correlate(Modulo)
        .scalar_subquery()
    )
    mod_rows = (
        await db.execute(
            select(Modulo, total_aulas.label("total_aulas"))
            .where(Modulo.curso_id == curso.id)
            .order_by(Modulo.ordem)
        )
    ).all()

    return CursoDetail(
        id=curso.id,
        slug=curso.slug,
        titulo=curso.titulo,
        descricao=curso.descricao,
        tipo=curso.tipo,
        preco=curso.preco,
        validade_dias=curso.validade_dias,
        thumbnail_url=curso.thumbnail_url,
        modulos=[
            ModuloResumo(
                id=m.id,
                titulo=m.titulo,
                ordem=m.ordem,
                total_aulas=n_aulas,
            )
            for m, n_aulas in mod_rows
        ],
    )

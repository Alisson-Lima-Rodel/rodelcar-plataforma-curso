from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import panda
from app.core.config import settings
from app.core.db import get_db
from app.dependencies import get_current_aluno
from app.models import Aluno, Aula, Curso, Modulo, StatusCurso, TipoCurso
from app.routers.avaliacoes import media_e_total
from app.schemas.cursos import (
    AulaPreview,
    AulaResumo,
    CursoDetail,
    CursoListItem,
    CursoListResponse,
    ModuloDetalhe,
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


def _dur_label(segundos: int | None) -> str:
    m, s = divmod(int(segundos or 0), 60)
    return f"{m:02d}:{s:02d}"


def _horas_label(segundos: int | None) -> str | None:
    """Soma de durações (s) → '8h40' (tempo total de vídeo do curso). 0 → None."""
    total = int(segundos or 0)
    if total <= 0:
        return None
    h, resto = divmod(total, 3600)
    m = resto // 60
    return f"{h}h{m:02d}"


@router.get("", response_model=CursoListResponse)
async def listar_cursos(
    tipo: TipoCurso | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Vitrine pública de cursos, com contagem de módulos e aulas + campos de venda."""
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
    aulas_gratis = (
        select(func.count(Aula.id))
        .select_from(Aula)
        .join(Modulo, Aula.modulo_id == Modulo.id)
        .where(Modulo.curso_id == Curso.id, Aula.gratuita.is_(True))
        .correlate(Curso)
        .scalar_subquery()
    )
    total_duracao = (
        select(func.coalesce(func.sum(Aula.duracao_segundos), 0))
        .select_from(Aula)
        .join(Modulo, Aula.modulo_id == Modulo.id)
        .where(Modulo.curso_id == Curso.id)
        .correlate(Curso)
        .scalar_subquery()
    )

    # Só cursos ATIVOS na vitrine pública (em desenvolvimento/inativo somem do
    # site; inativo continua acessível a quem já comprou — barrado por matrícula).
    base = select(Curso).where(Curso.status == StatusCurso.ativo)
    count_stmt = select(func.count(Curso.id)).where(Curso.status == StatusCurso.ativo)
    if tipo is not None:
        base = base.where(Curso.tipo == tipo)
        count_stmt = count_stmt.where(Curso.tipo == tipo)

    total = await db.scalar(count_stmt) or 0

    stmt = (
        base.add_columns(
            total_modulos.label("total_modulos"),
            total_aulas.label("total_aulas"),
            aulas_gratis.label("aulas_gratis"),
            total_duracao.label("total_duracao"),
        )
        .order_by(Curso.ordem, Curso.titulo)
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
            preco_antigo=curso.preco_antigo,
            validade_dias=curso.validade_dias,
            thumbnail_url=curso.thumbnail_url,
            gratuito=curso.gratuito,
            total_modulos=n_modulos,
            total_aulas=n_aulas,
            tem_preview=n_gratis > 0,
            destaque=curso.destaque,
            tagline=curso.tagline,
            # Calculados do conteúdo (não dos campos manuais antigos).
            horas=_horas_label(n_duracao),
            aulas_total=n_aulas,
            rating=curso.rating,
            nivel=curso.nivel,
            icon=curso.icon,
            badge_label=curso.badge_label,
        )
        for curso, n_modulos, n_aulas, n_gratis, n_duracao in rows
    ]
    return CursoListResponse(items=items, total=total, page=page, size=size)


@router.get("/{slug}/preview", response_model=list[AulaPreview])
async def aulas_preview(
    slug: str,
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    """Aulas grátis do curso, com o id do vídeo. Exige LOGIN (captura o lead antes
    de liberar a amostra) — expõe `panda_video_id` SÓ de aulas marcadas como
    gratuitas, e só para aluno cadastrado (as pagas nunca vazam)."""
    curso = (
        await db.execute(
            select(Curso.id).where(
                Curso.slug == slug, Curso.status == StatusCurso.ativo
            )
        )
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
    rows = (
        await db.execute(
            select(Aula)
            .join(Modulo, Aula.modulo_id == Modulo.id)
            .where(Modulo.curso_id == curso, Aula.gratuita.is_(True))
            .order_by(Modulo.ordem, Aula.ordem)
        )
    ).scalars().all()
    # Sob DRM, até a amostra grátis precisa do token assinado p/ tocar.
    token = panda.assinar_drm_token()
    grupo = settings.PANDA_DRM_GROUP_ID if token else None
    return [
        AulaPreview(
            id=a.id,
            titulo=a.titulo,
            # Embed usa o video_external_id (?v=); cai no id da API se não sincronizado.
            panda_video_id=a.panda_external_id or a.panda_video_id,
            player_token=token,
            drm_group_id=grupo,
        )
        for a in rows
    ]


@router.get("/{slug}", response_model=CursoDetail)
async def obter_curso(slug: str, db: AsyncSession = Depends(get_db)):
    """Detalhe da página de venda, com a estrutura de módulos e suas aulas."""
    curso = (
        await db.execute(
            select(Curso)
            .where(Curso.slug == slug, Curso.status == StatusCurso.ativo)
            .options(selectinload(Curso.modulos).selectinload(Modulo.aulas))
        )
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

    modulos = [
        ModuloDetalhe(
            id=m.id,
            titulo=m.titulo,
            ordem=m.ordem,
            total_aulas=len(m.aulas),
            aulas=[
                AulaResumo(
                    id=a.id,
                    titulo=a.titulo,
                    duracao_label=_dur_label(a.duracao_segundos),
                    gratuita=a.gratuita,
                )
                for a in m.aulas
            ],
        )
        for m in curso.modulos
    ]

    rating_medio, rating_count = await media_e_total(db, curso.id)

    # Calculados do conteúdo (nº de aulas e tempo total de vídeo).
    total_aulas = sum(len(m.aulas) for m in curso.modulos)
    total_duracao = sum(a.duracao_segundos for m in curso.modulos for a in m.aulas)

    return CursoDetail(
        id=curso.id,
        slug=curso.slug,
        titulo=curso.titulo,
        descricao=curso.descricao,
        tipo=curso.tipo,
        preco=curso.preco,
        preco_antigo=curso.preco_antigo,
        validade_dias=curso.validade_dias,
        thumbnail_url=curso.thumbnail_url,
        gratuito=curso.gratuito,
        tagline=curso.tagline,
        horas=_horas_label(total_duracao),
        aulas_total=total_aulas,
        rating=curso.rating,
        nivel=curso.nivel,
        icon=curso.icon,
        badge_label=curso.badge_label,
        aprende=curso.aprende or [],
        idiomas_legenda=curso.idiomas_legenda or [],
        modulos=modulos,
        rating_medio=rating_medio,
        rating_count=rating_count,
    )

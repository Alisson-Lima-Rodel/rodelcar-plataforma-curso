from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Faq, GoogleReviewCache, PlanoAssinatura, TurmaMidia, Video
from app.schemas.pagamentos import PlanoPublico
from app.schemas.portal import (
    FaqPublico,
    GoogleReviewsPublico,
    TurmaMidiaPublico,
    VideoPublico,
)

router = APIRouter(tags=["conteudo"])


@router.get("/videos", response_model=list[VideoPublico])
async def listar_videos(db: AsyncSession = Depends(get_db)):
    """Vídeos ativos para a prova social do portal (público)."""
    rows = (
        await db.execute(
            select(Video)
            .where(Video.status == "Ativo")
            .order_by(Video.ordem, Video.criado_em)
            .limit(100)  # teto defensivo p/ resposta pública
        )
    ).scalars().all()
    return rows


@router.get("/planos", response_model=list[PlanoPublico])
async def listar_planos(db: AsyncSession = Depends(get_db)):
    """Planos de assinatura ativos (público — alimenta o card Premium da vitrine).

    O checkout em si exige login (`POST /checkout/assinatura-cartao`); aqui só os
    dados de exibição + o id do plano. `stripe_price_id` não é exposto.
    """
    rows = (
        await db.execute(
            select(PlanoAssinatura)
            .where(PlanoAssinatura.status == "Ativo")
            .order_by(PlanoAssinatura.ordem, PlanoAssinatura.criado_em)
            .limit(20)
        )
    ).scalars().all()
    return rows


@router.get("/google-reviews", response_model=GoogleReviewsPublico)
async def google_reviews(db: AsyncSession = Depends(get_db)):
    """Nota e avaliações da ficha do Google (lidas do cache). Vazio se ainda não
    sincronizou ou se a integração não está configurada."""
    row = await db.get(GoogleReviewCache, 1)
    if row is None or not row.total:
        return GoogleReviewsPublico(rating=None, total=0, reviews=[])
    return GoogleReviewsPublico(
        rating=float(row.rating) if row.rating is not None else None,
        total=row.total,
        reviews=row.reviews or [],
    )


@router.get("/faq", response_model=list[FaqPublico])
async def listar_faq(db: AsyncSession = Depends(get_db)):
    """Perguntas frequentes ativas (público)."""
    rows = (
        await db.execute(
            select(Faq)
            .where(Faq.status == "Ativo")
            .order_by(Faq.ordem, Faq.criado_em)
            .limit(100)  # teto defensivo p/ resposta pública
        )
    ).scalars().all()
    return rows


@router.get("/turmas-midia", response_model=list[TurmaMidiaPublico])
async def listar_turmas_midia(db: AsyncSession = Depends(get_db)):
    """Fotos das turmas presenciais ativas (mosaico bento da home — público)."""
    rows = (
        await db.execute(
            select(TurmaMidia)
            .where(TurmaMidia.status == "Ativo")
            .order_by(TurmaMidia.ordem, TurmaMidia.criado_em)
            .limit(100)  # teto defensivo p/ resposta pública
        )
    ).scalars().all()
    return rows

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Faq, Video
from app.schemas.portal import FaqPublico, VideoPublico

router = APIRouter(tags=["conteudo"])


@router.get("/videos", response_model=list[VideoPublico])
async def listar_videos(db: AsyncSession = Depends(get_db)):
    """Vídeos ativos para a prova social do portal (público)."""
    rows = (
        await db.execute(
            select(Video)
            .where(Video.status == "Ativo")
            .order_by(Video.ordem, Video.criado_em)
        )
    ).scalars().all()
    return rows


@router.get("/faq", response_model=list[FaqPublico])
async def listar_faq(db: AsyncSession = Depends(get_db)):
    """Perguntas frequentes ativas (público)."""
    rows = (
        await db.execute(
            select(Faq)
            .where(Faq.status == "Ativo")
            .order_by(Faq.ordem, Faq.criado_em)
        )
    ).scalars().all()
    return rows

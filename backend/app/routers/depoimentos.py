from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Depoimento
from app.schemas.depoimentos import DepoimentoPublico

router = APIRouter(prefix="/depoimentos", tags=["depoimentos"])


@router.get("", response_model=list[DepoimentoPublico])
async def listar_depoimentos(db: AsyncSession = Depends(get_db)):
    """Depoimentos aprovados para a prova social do portal (público)."""
    rows = (
        await db.execute(
            select(Depoimento)
            .where(Depoimento.status == "Aprovado")
            .order_by(Depoimento.ordem, Depoimento.criado_em)
        )
    ).scalars().all()
    return rows

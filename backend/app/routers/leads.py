from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import Lead
from app.schemas.leads import LeadCreate, LeadCreated

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadCreated, status_code=201)
async def criar_lead(body: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Captação pública de lead (agendamento de avaliação no portal).

    Protegido pelo rate limit padrão por IP (SlowAPIMiddleware). O `status` nasce
    como `novo`; o follow-up comercial é feito depois no painel.
    """
    lead = Lead(
        nome=body.nome,
        telefone=body.telefone,
        email=body.email,
        tipo_servico=body.tipo_servico,
        mensagem=body.mensagem,
        origem=body.origem,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead

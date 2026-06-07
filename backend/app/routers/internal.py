"""Endpoints internos — autenticados por X-Internal-Token (servidor a servidor)."""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.ratelimit import limiter
from app.core.scheduler import executar_ciclo_vigencia

router = APIRouter(prefix="/internal", tags=["internal"])


def _verificar_token(x_internal_token: str | None = Header(None)) -> None:
    if not x_internal_token or x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "NAO_AUTORIZADO",
                    "message": "Token interno inválido ou ausente.",
                    "details": None,
                }
            },
        )


class ProcessarRequest(BaseModel):
    marcos: list[str] = ["15d", "7d", "1d", "expirado"]
    dry_run: bool = False


@router.post("/notificacoes/processar", dependencies=[Depends(_verificar_token)])
@limiter.exempt
async def processar_notificacoes(body: ProcessarRequest | None = None):
    dry_run = body.dry_run if body else False
    return await executar_ciclo_vigencia(dry_run=dry_run)

import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models import Aluno

_bearer = HTTPBearer(auto_error=False)


async def get_current_aluno(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Aluno:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "NAO_AUTENTICADO", "message": "Token de acesso necessário.", "details": None}},
        )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("not access token")
        aluno_uuid = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "TOKEN_INVALIDO", "message": "Token inválido ou expirado.", "details": None}},
        )

    result = await db.execute(select(Aluno).where(Aluno.id == aluno_uuid))
    aluno = result.scalar_one_or_none()
    if aluno is None:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "ALUNO_NAO_ENCONTRADO", "message": "Aluno não encontrado.", "details": None}},
        )
    return aluno

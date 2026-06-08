import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models import Admin, Aluno

_bearer = HTTPBearer(auto_error=False)


def _unauth(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


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


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    if credentials is None:
        raise _unauth("NAO_AUTENTICADO", "Token de admin necessário.")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "admin_access":
            raise jwt.InvalidTokenError("not admin token")
        admin_uuid = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauth("TOKEN_INVALIDO", "Token inválido ou expirado.")

    admin = (await db.execute(select(Admin).where(Admin.id == admin_uuid))).scalar_one_or_none()
    if admin is None or not admin.ativo:
        raise _unauth("ADMIN_NAO_ENCONTRADO", "Administrador não encontrado ou inativo.")
    return admin

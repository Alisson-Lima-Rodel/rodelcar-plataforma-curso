import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.ratelimit import auth_limit, limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    dummy_verify,
    hash_password,
    verify_password,
)
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.models import Aluno, Matricula, RefreshToken, StatusMatricula
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message, "details": None}},
    )


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _emitir_tokens(aluno_id: str, db: AsyncSession) -> TokenResponse:
    """Emite par access+refresh e persiste o refresh (jti) p/ rotação/revogação."""
    access = create_access_token(aluno_id)
    refresh_token, jti = create_refresh_token(aluno_id)
    db.add(
        RefreshToken(
            aluno_id=uuid.UUID(aluno_id),
            jti=uuid.UUID(jti),
            expira_em=datetime.now(timezone.utc)
            + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
        )
    )
    await db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(auth_limit)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Aluno).where(Aluno.email == body.email))
    aluno = result.scalar_one_or_none()

    # Equaliza o tempo de resposta quando o e-mail não existe (anti-enumeração).
    if aluno is None:
        dummy_verify()
        raise _err(401, "CREDENCIAIS_INVALIDAS", "Email ou senha incorretos.")
    if not verify_password(body.senha, aluno.senha_hash):
        raise _err(401, "CREDENCIAIS_INVALIDAS", "Email ou senha incorretos.")
    await checar_vigencia_aluno(aluno.id, db)
    return await _emitir_tokens(str(aluno.id), db)


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit(auth_limit)
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Cria a conta do aluno e já devolve o par de tokens (auto-login)."""
    existe = await db.scalar(select(Aluno.id).where(Aluno.email == body.email))
    if existe is not None:
        raise _err(409, "EMAIL_JA_CADASTRADO", "Já existe uma conta com esse e-mail.")
    aluno = Aluno(nome=body.nome, email=body.email, senha_hash=hash_password(body.senha))
    db.add(aluno)
    await db.flush()  # gera aluno.id
    return await _emitir_tokens(str(aluno.id), db)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(auth_limit)
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("not refresh token")
        aluno_uuid = uuid.UUID(payload["sub"])
        jti = uuid.UUID(payload["jti"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _err(401, "REFRESH_INVALIDO", "Refresh token inválido ou expirado.")

    rt = (
        await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    ).scalar_one_or_none()
    agora = datetime.now(timezone.utc)

    # jti desconhecido (forjado) ou pertencente a outro aluno → recusa.
    if rt is None or rt.aluno_id != aluno_uuid:
        raise _err(401, "REFRESH_INVALIDO", "Refresh token inválido ou expirado.")

    # Reuso de token já rotacionado = sinal de roubo → revoga a família inteira.
    if rt.revogado:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.aluno_id == aluno_uuid, RefreshToken.revogado.is_(False))
            .values(revogado=True, revogado_em=agora)
        )
        await db.commit()
        raise _err(
            401,
            "REFRESH_REUTILIZADO",
            "Refresh token reutilizado — todas as sessões foram revogadas. Faça login novamente.",
        )

    if _aware(rt.expira_em) < agora:
        raise _err(401, "REFRESH_INVALIDO", "Refresh token inválido ou expirado.")

    # Rotação: revoga o token atual e emite um novo par (commit atômico em _emitir_tokens).
    rt.revogado = True
    rt.revogado_em = agora
    return await _emitir_tokens(str(aluno_uuid), db)


@router.post("/logout", status_code=204)
@limiter.limit(auth_limit)
async def logout(
    request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    """Revoga o refresh token informado (idempotente)."""
    try:
        payload = decode_token(body.refresh_token)
        jti = uuid.UUID(payload["jti"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return Response(status_code=204)  # nada a fazer; não vaza se era válido

    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.jti == jti, RefreshToken.revogado.is_(False))
        .values(revogado=True, revogado_em=datetime.now(timezone.utc))
    )
    await db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
async def me(
    aluno: Aluno = Depends(get_current_aluno),
    db: AsyncSession = Depends(get_db),
):
    count = await db.scalar(
        select(func.count()).select_from(Matricula).where(
            Matricula.aluno_id == aluno.id,
            Matricula.status == StatusMatricula.ativo,
        )
    )
    return MeResponse(
        id=aluno.id,
        nome=aluno.nome,
        email=aluno.email,
        matriculas_ativas=count or 0,
    )

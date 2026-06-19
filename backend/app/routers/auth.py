import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
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
    hash_reset_token,
    verify_password,
)
from app.core.referral import codigo_unico_indicacao
from app.core.vigencia import checar_vigencia_aluno
from app.dependencies import get_current_aluno
from app.models import (
    Aluno,
    Evento,
    Indicacao,
    Matricula,
    PasswordReset,
    RefreshToken,
    StatusMatricula,
)
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    ResetSenhaConfirm,
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


async def _emitir_tokens(aluno_id: str, token_version: int, db: AsyncSession) -> TokenResponse:
    """Emite par access+refresh e persiste o refresh (jti) p/ rotação/revogação."""
    access = create_access_token(aluno_id, token_version)
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
    # Acesso bloqueado manualmente pelo admin: barra o login até ser liberado.
    if aluno.bloqueado:
        raise _err(403, "ALUNO_BLOQUEADO", "Acesso bloqueado. Fale com o suporte.")
    await checar_vigencia_aluno(aluno.id, db)
    # Registra o acesso (alimenta o gráfico diário da visão geral do admin).
    db.add(Evento(aluno_id=aluno.id, nome_evento="login"))
    return await _emitir_tokens(str(aluno.id), aluno.token_version, db)


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit(auth_limit)
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Cria a conta do aluno e já devolve o par de tokens (auto-login)."""
    existe = await db.scalar(select(Aluno.id).where(Aluno.email == body.email))
    if existe is not None:
        raise _err(409, "EMAIL_JA_CADASTRADO", "Já existe uma conta com esse e-mail.")

    # Resolve o indicador ANTES de criar a conta (código inválido = ignora, não
    # bloqueia o cadastro). Auto-indicação é impossível: o indicador é uma conta
    # pré-existente e o novo aluno ainda não tem código.
    indicador_id = None
    if body.codigo_indicacao:
        indicador_id = await db.scalar(
            select(Aluno.id).where(
                Aluno.codigo_indicacao == body.codigo_indicacao.strip().upper()
            )
        )

    # Cria a conta com retry: a corrida no `codigo_indicacao` (TOCTOU do SELECT de
    # unicidade) ou um e-mail tomado em paralelo viram IntegrityError — tratamos
    # em vez de estourar 500.
    senha_hash = hash_password(body.senha)
    aluno = None
    for _ in range(3):
        aluno = Aluno(
            nome=body.nome,
            email=body.email,
            senha_hash=senha_hash,
            codigo_indicacao=await codigo_unico_indicacao(db),
        )
        db.add(aluno)
        try:
            await db.flush()  # gera aluno.id; dispara unique de email/codigo
            break
        except IntegrityError:
            await db.rollback()
            if await db.scalar(select(Aluno.id).where(Aluno.email == body.email)):
                raise _err(409, "EMAIL_JA_CADASTRADO", "Já existe uma conta com esse e-mail.")
            aluno = None  # colisão de código → tenta de novo
    if aluno is None:  # pragma: no cover (colisão repetida é praticamente impossível)
        raise _err(409, "CADASTRO_CONFLITO", "Não foi possível concluir. Tente novamente.")
    if indicador_id is not None and indicador_id != aluno.id:
        db.add(Indicacao(indicador_id=indicador_id, indicado_id=aluno.id))
    return await _emitir_tokens(str(aluno.id), aluno.token_version, db)


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

    # Reuso de token já rotacionado = sinal de roubo → revoga a família inteira E
    # incrementa token_version (mata também os access tokens vivos, não só os refresh).
    if rt.revogado:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.aluno_id == aluno_uuid, RefreshToken.revogado.is_(False))
            .values(revogado=True, revogado_em=agora)
        )
        await db.execute(
            update(Aluno)
            .where(Aluno.id == aluno_uuid)
            .values(token_version=Aluno.token_version + 1)
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
    aluno = await db.get(Aluno, aluno_uuid)
    # Aluno bloqueado não renova sessão (mesmo com refresh válido). O access já
    # cairia em get_current_aluno, mas barrar aqui evita rotacionar a família.
    if aluno is None or aluno.bloqueado:
        await db.commit()  # persiste a revogação do token atual
        raise _err(403, "ALUNO_BLOQUEADO", "Acesso bloqueado. Fale com o suporte.")
    return await _emitir_tokens(str(aluno_uuid), aluno.token_version, db)


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


@router.post("/recuperar-senha/confirmar", status_code=204)
@limiter.limit(auth_limit)
async def confirmar_recuperar_senha(
    request: Request, body: ResetSenhaConfirm, db: AsyncSession = Depends(get_db)
):
    """Redefine a senha a partir do token gerado pelo admin (link enviado ao
    aluno). Token single-use, comparado por hash. Ao concluir, incrementa o
    token_version (derruba sessões vivas) e marca o token como usado."""
    pr = (
        await db.execute(
            select(PasswordReset).where(
                PasswordReset.token_hash == hash_reset_token(body.token)
            )
        )
    ).scalar_one_or_none()
    if pr is None or pr.usado or _aware(pr.expira_em) < datetime.now(timezone.utc):
        raise _err(400, "TOKEN_INVALIDO", "Link inválido ou expirado. Peça um novo.")

    aluno = await db.get(Aluno, pr.aluno_id)
    if aluno is None:
        raise _err(400, "TOKEN_INVALIDO", "Link inválido ou expirado. Peça um novo.")

    aluno.senha_hash = hash_password(body.nova_senha)
    aluno.token_version += 1
    pr.usado = True
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

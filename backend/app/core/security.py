import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# Hash dummy fixo (custo de um verify real) para equalizar o tempo de resposta
# quando o e-mail não existe — mitiga enumeração de contas por timing no login.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equalization-dummy", bcrypt.gensalt())


def dummy_verify() -> None:
    """Gasta ~o mesmo tempo de um verify_password real, sem revelar nada."""
    bcrypt.checkpw(b"x", _DUMMY_HASH)


def _make_token(data: dict, expires_delta: timedelta) -> str:
    payload = {**data, "exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(sub: str) -> str:
    return _make_token(
        {"sub": sub, "type": "access"},
        timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
    )


def create_admin_token(sub: str) -> str:
    """Token de acesso do painel admin — `type` distinto p/ não cruzar com aluno."""
    return _make_token(
        {"sub": sub, "type": "admin_access"},
        timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
    )


def create_refresh_token(sub: str) -> tuple[str, str]:
    """Retorna (token, jti). O jti referencia a linha em refresh_tokens p/ rotação."""
    jti = str(uuid.uuid4())
    token = _make_token(
        {"sub": sub, "type": "refresh", "jti": jti},
        timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
    )
    return token, jti


def decode_token(token: str) -> dict:
    # algorithms explícito evita ataque de confusão de algoritmo (alg=none/HS↔RS).
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

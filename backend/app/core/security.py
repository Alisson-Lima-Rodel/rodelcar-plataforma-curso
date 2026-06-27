import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def gerar_reset_token() -> tuple[str, str]:
    """Gera (token_bruto, token_hash) p/ redefinição de senha.

    O bruto vai no link (entregue UMA vez ao admin); só o SHA-256 é persistido.
    Comparação por hash evita vazar tokens válidos caso a tabela seja lida.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hash_reset_token(raw)


def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


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


def create_access_token(sub: str, token_version: int = 0) -> str:
    return _make_token(
        {"sub": sub, "type": "access", "tv": token_version},
        timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
    )


def create_admin_token(sub: str, token_version: int = 0) -> str:
    """Token de acesso do painel admin — `type` distinto p/ não cruzar com aluno."""
    return _make_token(
        {"sub": sub, "type": "admin_access", "tv": token_version},
        timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
    )


def create_admin_refresh_token(sub: str, token_version: int = 0) -> str:
    """Refresh do painel admin (stateless). Carrega `tv`: o logout bumpa o
    token_version e invalida access E refresh de uma vez. `type` distinto evita
    cruzar com o refresh do aluno (que é stateful, com jti)."""
    return _make_token(
        {"sub": sub, "type": "admin_refresh", "tv": token_version},
        timedelta(days=settings.JWT_ADMIN_REFRESH_EXPIRE_DAYS),
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

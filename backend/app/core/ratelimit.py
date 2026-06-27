"""Rate limiting por IP (slowapi), padrão de toda a API.

O limite default é aplicado a **todas** as rotas pela `SlowAPIMiddleware`
(registrada em app.main) — endpoints novos já nascem protegidos, sem precisar
decorar um a um. Para um teto diferente em uma rota específica, use o decorator
`@limiter.limit("<limite>")` no handler (exige `request: Request` na assinatura).
"""
import logging
from functools import lru_cache

from limits import parse
from limits.storage import storage_from_string
from limits.strategies import FixedWindowRateLimiter
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback seguro caso RATE_LIMIT_PUBLIC venha em formato inválido (ex.: "100/min").
_DEFAULT_LIMIT = "120/minute"


@lru_cache(maxsize=8)
def _validated(value: str) -> str:
    """Valida o formato do limite (lib `limits`); cai no default se inválido.

    Um valor de env mal formatado NÃO pode derrubar a API — sem isso, o parser
    lança ValueError em toda requisição e vira 500. O cache evita logar repetido.
    """
    try:
        parse(value)
        return value
    except ValueError:
        logger.warning(
            "RATE_LIMIT_PUBLIC inválido (%r) — usando %s. "
            "Formato esperado: '120/minute', '100 per minute', '5/second'.",
            value, _DEFAULT_LIMIT,
        )
        return _DEFAULT_LIMIT


def public_limit() -> str:
    """Limite avaliado por requisição — permite ajustar via env sem reimportar."""
    return _validated(settings.RATE_LIMIT_PUBLIC)


def auth_limit() -> str:
    """Teto estrito p/ login/refresh (anti brute-force)."""
    return _validated(settings.RATE_LIMIT_AUTH)


# Storage: memória por padrão (ok p/ dev e 1 instância). Em produção
# multi-instância/multi-worker, defina RATELIMIT_STORAGE_URI=redis://... para
# que o contador seja compartilhado — senão cada processo conta sozinho.
_storage_uri = settings.RATELIMIT_STORAGE_URI or None
if not _storage_uri and settings.is_production:
    logger.warning(
        "RATELIMIT_STORAGE_URI não definido em produção — rate limit fica "
        "POR PROCESSO (não compartilhado entre instâncias/workers). "
        "Configure redis://... para um teto global."
    )

# default_limits aceita callables: o teto é lido de settings a cada requisição.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[public_limit],
    storage_uri=_storage_uri,
)

# ── Teto de FALHAS de login POR CONTA (e-mail), além do teto por IP ───────────
# Freia brute-force horizontal (muitos IPs contra uma conta). Reusa o mesmo
# storage (memória em dev; Redis em produção via RATELIMIT_STORAGE_URI). Só
# falhas consomem o orçamento (`registrar_falha_login`); o login bem-sucedido
# nunca chama `hit` → não há lockout duro nem DoS de bloqueio da vítima.
_conta_storage = storage_from_string(_storage_uri or "memory://")
_conta_strategy = FixedWindowRateLimiter(_conta_storage)


def conta_login_bloqueada(email: str) -> bool:
    """True se a conta já estourou o teto de falhas na janela (checa SEM consumir)."""
    item = parse(_validated(settings.RATE_LIMIT_AUTH_ACCOUNT))
    return not _conta_strategy.test(item, "login", email)


def registrar_falha_login(email: str) -> None:
    """Consome 1 do orçamento de falhas da conta — chamado só em senha errada."""
    item = parse(_validated(settings.RATE_LIMIT_AUTH_ACCOUNT))
    _conta_strategy.hit(item, "login", email)


def reset_conta() -> None:
    """Zera o contador por conta (usado entre testes)."""
    _conta_storage.reset()

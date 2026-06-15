"""Cupons de desconto na Stripe (Coupon + Promotion Code).

O admin cria um cupom no painel → criamos um Coupon (o desconto) e um Promotion
Code (o texto que o cliente digita) na Stripe. O Checkout usa `allow_promotion_codes`
e o cliente aplica o código na tela hospedada. O desconto é IMUTÁVEL na Stripe.
"""

import logging
from decimal import Decimal

import stripe
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)


def stripe_ativo() -> bool:
    if not settings.STRIPE_SECRET_KEY:
        return False
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return True


def _centavos(valor: float) -> int:
    return int((Decimal(str(valor)) * 100).to_integral_value())


async def criar_cupom_stripe(
    codigo: str,
    tipo: str,
    valor: float,
    *,
    max_resgates: int | None = None,
    validade_ts: int | None = None,
) -> tuple[str, str]:
    """Cria Coupon + Promotion Code (duration=once). Retorna (coupon_id, promo_id)."""
    if tipo == "percentual":
        coupon = await run_in_threadpool(
            stripe.Coupon.create, percent_off=float(valor), duration="once"
        )
    else:  # valor fixo (R$)
        coupon = await run_in_threadpool(
            stripe.Coupon.create,
            amount_off=_centavos(valor),
            currency="brl",
            duration="once",
        )
    promo_kwargs: dict = {"coupon": coupon.id, "code": codigo}
    if max_resgates:
        promo_kwargs["max_redemptions"] = max_resgates
    if validade_ts:
        promo_kwargs["expires_at"] = validade_ts
    promo = await run_in_threadpool(stripe.PromotionCode.create, **promo_kwargs)
    return coupon.id, promo.id


async def set_cupom_ativo(promotion_code_id: str, ativo: bool) -> None:
    """Liga/desliga o Promotion Code (o Coupon em si é imutável)."""
    await run_in_threadpool(
        stripe.PromotionCode.modify, promotion_code_id, active=ativo
    )


async def arquivar_cupom_stripe(promotion_code_id: str | None) -> None:
    """Best-effort: desativa o Promotion Code (exclusão no admin)."""
    if not promotion_code_id:
        return
    try:
        await run_in_threadpool(
            stripe.PromotionCode.modify, promotion_code_id, active=False
        )
    except stripe.error.StripeError:
        logger.warning(
            "Falha ao desativar promotion code %s — exclusão local segue.",
            promotion_code_id,
        )

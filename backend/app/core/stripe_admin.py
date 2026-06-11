"""Sincronização do catálogo (cursos/planos) com a Stripe a partir do painel admin.

Prices da Stripe são IMUTÁVEIS: mudar o preço = criar um Price novo no mesmo
Product e desativar o antigo. Assinaturas já vendidas continuam no Price em que
foram contratadas (comportamento padrão da Stripe); o Price novo vale para as
PRÓXIMAS vendas. Excluir no admin arquiva (active=false) — nunca apaga histórico.
"""

import logging
from decimal import Decimal

import stripe
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)

_INTERVALO_STRIPE = {"mensal": "month", "anual": "year"}


def stripe_ativo() -> bool:
    """Stripe configurado? Sem chave, o admin opera só no banco (modo dev)."""
    if not settings.STRIPE_SECRET_KEY:
        return False
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return True


def _centavos(preco: float) -> int:
    return int((Decimal(str(preco)) * 100).to_integral_value())


async def criar_price_curso(titulo: str, slug: str, preco: float) -> str:
    """Product + Price one-time (BRL) para um curso avulso. Retorna o price_id."""
    product = await run_in_threadpool(
        stripe.Product.create, name=titulo, metadata={"curso_slug": slug}
    )
    price = await run_in_threadpool(
        stripe.Price.create,
        product=product.id,
        currency="brl",
        unit_amount=_centavos(preco),
    )
    return price.id


async def criar_price_plano(nome: str, intervalo: str, preco: float) -> str:
    """Product + Price recorrente (BRL) para um plano de assinatura."""
    product = await run_in_threadpool(
        stripe.Product.create, name=nome, metadata={"plano_intervalo": intervalo}
    )
    price = await run_in_threadpool(
        stripe.Price.create,
        product=product.id,
        currency="brl",
        unit_amount=_centavos(preco),
        recurring={"interval": _INTERVALO_STRIPE[intervalo]},
    )
    return price.id


async def _product_do_price(price_id: str) -> str:
    price = await run_in_threadpool(stripe.Price.retrieve, price_id)
    product = price["product"]
    return product["id"] if isinstance(product, dict) else product


async def renomear_produto(price_id: str, nome: str) -> None:
    product_id = await _product_do_price(price_id)
    await run_in_threadpool(stripe.Product.modify, product_id, name=nome)


async def trocar_preco(
    price_id: str, novo_preco: float, intervalo: str | None = None
) -> str:
    """Price novo no mesmo Product e desativa o antigo. Retorna o novo price_id.

    `intervalo` (mensal|anual) só para planos — None mantém o Price one-time.
    """
    product_id = await _product_do_price(price_id)
    kwargs: dict = {
        "product": product_id,
        "currency": "brl",
        "unit_amount": _centavos(novo_preco),
    }
    if intervalo:
        kwargs["recurring"] = {"interval": _INTERVALO_STRIPE[intervalo]}
    novo = await run_in_threadpool(stripe.Price.create, **kwargs)
    await run_in_threadpool(stripe.Price.modify, price_id, active=False)
    return novo.id


async def arquivar_price(price_id: str) -> None:
    """Best-effort: desativa Price e Product na Stripe (exclusão no admin)."""
    try:
        product_id = await _product_do_price(price_id)
        await run_in_threadpool(stripe.Price.modify, price_id, active=False)
        await run_in_threadpool(stripe.Product.modify, product_id, active=False)
    except stripe.error.StripeError:
        logger.warning(
            "Falha ao arquivar %s na Stripe — exclusão local segue mesmo assim.",
            price_id,
        )

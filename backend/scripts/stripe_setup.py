"""Cria os Products/Prices (BRL) no Stripe para os cursos avulsos e grava o
`stripe_price_id` em cada curso.

Uso (modo TESTE — use uma sk_test_...):
    docker compose run --rm --entrypoint python backend -m scripts.stripe_setup
    # ou, fora do Docker, com STRIPE_SECRET_KEY e DATABASE_URL no ambiente:
    cd backend && python -m scripts.stripe_setup

Idempotente: cursos que já têm `stripe_price_id` são pulados. Atende ao
"criar os Prices uma vez e referenciar só o price_id" — sem fixar valor no checkout.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Curso, TipoCurso


async def main() -> None:
    if not settings.STRIPE_SECRET_KEY:
        print("! STRIPE_SECRET_KEY ausente — defina no .env antes de rodar.")
        return
    stripe.api_key = settings.STRIPE_SECRET_KEY

    engine = create_async_engine(settings.DATABASE_URL, connect_args=settings.db_connect_args)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as s:
        cursos = (
            await s.execute(select(Curso).where(Curso.tipo == TipoCurso.avulso))
        ).scalars().all()

        for curso in cursos:
            if curso.stripe_price_id:
                print(f"= {curso.slug}: já tem price_id ({curso.stripe_price_id}), pulando.")
                continue

            product = stripe.Product.create(
                name=curso.titulo,
                metadata={"curso_slug": curso.slug},
            )
            price = stripe.Price.create(
                product=product.id,
                currency="brl",
                unit_amount=int((Decimal(str(curso.preco)) * 100).to_integral_value()),
            )
            curso.stripe_price_id = price.id
            await s.commit()
            print(f"+ {curso.slug}: product={product.id} price={price.id} (R$ {curso.preco})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

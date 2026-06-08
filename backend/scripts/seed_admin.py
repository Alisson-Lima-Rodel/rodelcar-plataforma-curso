"""Semeia um administrador de teste para o painel.

Uso:
    docker compose run --rm --entrypoint python backend -m scripts.seed_admin

Idempotente. Login de teste:  admin@rodelcar.com.br  /  Admin123!
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models import Admin, PapelAdmin

EMAIL = "admin@rodelcar.com.br"
SENHA = "Admin123!"


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, connect_args=settings.db_connect_args)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as s:
        if await s.scalar(select(Admin.id).where(Admin.email == EMAIL)):
            print(f"= {EMAIL} já existe, nada a fazer.")
        else:
            s.add(
                Admin(
                    nome="Rödel",
                    email=EMAIL,
                    senha_hash=hash_password(SENHA),
                    papel=PapelAdmin.administrador,
                )
            )
            await s.commit()
            print(f"+ admin {EMAIL} (senha {SENHA}) · papel Administrador")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

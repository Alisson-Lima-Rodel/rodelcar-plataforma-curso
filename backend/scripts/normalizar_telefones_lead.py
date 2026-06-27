"""Normaliza telefones de Lead já gravados para SÓ dígitos (DDD + número).

Leads criados antes da validação no schema ficaram com máscara
("(51) 99999-9999"). Este script de uso único limpa o histórico: remove tudo que
não é dígito e descarta o "55" do país quando vier com 12–13 dígitos — mesma
regra do validador `telefone_br`. É best-effort: telefones legados fora do padrão
BR (não 10/11 dígitos) são apenas reduzidos a dígitos, não descartados.

Rodar uma vez:
    docker compose run --rm --entrypoint python backend scripts/normalizar_telefones_lead.py
"""
import asyncio

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models import Lead


def _so_digitos(v: str | None) -> str | None:
    if not v:
        return v
    d = "".join(c for c in v if c.isdigit())
    if len(d) in (12, 13) and d.startswith("55"):
        d = d[2:]
    return d


async def main() -> None:
    alterados = 0
    async with AsyncSessionLocal() as db:
        leads = (await db.execute(select(Lead))).scalars().all()
        for lead in leads:
            novo = _so_digitos(lead.telefone)
            if novo is not None and novo != lead.telefone:
                lead.telefone = novo
                alterados += 1
        if alterados:
            await db.commit()
        print(f"Leads normalizados: {alterados} de {len(leads)}")


if __name__ == "__main__":
    asyncio.run(main())

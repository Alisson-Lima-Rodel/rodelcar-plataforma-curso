"""Popula o banco com cursos de exemplo (1 premium, 1 avulso "i-motion").

Uso (a partir de backend/):
    python -m scripts.seed

Idempotente: cursos já existentes (por slug) são ignorados.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Aula, Curso, Modulo, TipoCurso

# --------------------------------------------------------------------------- #
# Dados de exemplo. Cada aula é (titulo, duracao_segundos).
# --------------------------------------------------------------------------- #
CURSOS_SEED: list[dict] = [
    {
        "slug": "i-motion",
        "titulo": "Diagnóstico I-Motion",
        "descricao": (
            "Domine o câmbio automatizado I-Motion da Fiat: leitura de scanner, "
            "atuadores, embreagem e calibração. Da teoria ao reparo prático, com "
            "esquemas elétricos e casos reais de oficina."
        ),
        "tipo": TipoCurso.avulso,
        "preco": 497.00,
        "validade_dias": 365,
        "thumbnail_url": "https://cdn.rodelcar.com.br/cursos/i-motion.jpg",
        "destaque": False,
        "modulos": [
            {
                "titulo": "Fundamentos do I-Motion",
                "aulas": [
                    ("Visão geral do sistema", 540),
                    ("Componentes e atuadores", 720),
                    ("Hidráulica e bomba eletro-hidráulica", 660),
                ],
            },
            {
                "titulo": "Diagnóstico com scanner",
                "aulas": [
                    ("Conectando o scanner", 480),
                    ("Leitura de scanner e parâmetros", 1280),
                    ("Interpretação de códigos de falha", 900),
                ],
            },
            {
                "titulo": "Reparo e calibração",
                "aulas": [
                    ("Troca de embreagem", 1500),
                    ("Calibração do ponto de embreagem", 1100),
                    ("Teste de estrada e validação", 600),
                ],
            },
        ],
    },
    {
        "slug": "premium-mecanico-master",
        "titulo": "Trilha Premium — Mecânico Master de Câmbios",
        "descricao": (
            "Assinatura premium com a trilha completa de câmbios automáticos e "
            "automatizados: AL4, automáticos convencionais, CVT e dupla embreagem. "
            "Atualizações contínuas, materiais de apoio e certificado por curso."
        ),
        "tipo": TipoCurso.premium,
        "preco": 1490.00,
        "validade_dias": 365,
        "thumbnail_url": "https://cdn.rodelcar.com.br/cursos/premium-master.jpg",
        "destaque": True,
        "modulos": [
            {
                "titulo": "Câmbio automático convencional",
                "aulas": [
                    ("Conversor de torque", 820),
                    ("Trem de engrenagens planetárias", 980),
                    ("Corpo de válvulas", 1040),
                ],
            },
            {
                "titulo": "Transmissão CVT",
                "aulas": [
                    ("Princípio de funcionamento do CVT", 700),
                    ("Polias e correia/corrente", 760),
                    ("Diagnóstico de patinação", 880),
                ],
            },
            {
                "titulo": "Dupla embreagem (DCT)",
                "aulas": [
                    ("Arquitetura do DCT", 690),
                    ("Mecatrônica e adaptações", 1150),
                    ("Falhas comuns e soluções", 940),
                ],
            },
        ],
    },
]


async def _seed_curso(session, data: dict) -> bool:
    """Insere um curso (e sua árvore) se o slug ainda não existir.

    Retorna True se inseriu, False se já existia.
    """
    existe = await session.scalar(select(Curso.id).where(Curso.slug == data["slug"]))
    if existe is not None:
        return False

    curso = Curso(
        slug=data["slug"],
        titulo=data["titulo"],
        descricao=data["descricao"],
        tipo=data["tipo"],
        preco=data["preco"],
        validade_dias=data["validade_dias"],
        thumbnail_url=data["thumbnail_url"],
        destaque=data["destaque"],
    )
    for m_idx, mod in enumerate(data["modulos"], start=1):
        modulo = Modulo(titulo=mod["titulo"], ordem=m_idx)
        for a_idx, (titulo, duracao) in enumerate(mod["aulas"], start=1):
            modulo.aulas.append(
                Aula(titulo=titulo, duracao_segundos=duracao, ordem=a_idx)
            )
        curso.modulos.append(modulo)

    session.add(curso)
    return True


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    inseridos = 0
    async with Session() as session:
        for data in CURSOS_SEED:
            if await _seed_curso(session, data):
                inseridos += 1
                print(f"  + {data['slug']} ({data['tipo'].value})")
            else:
                print(f"  = {data['slug']} já existe, ignorado")
        await session.commit()

    await engine.dispose()
    print(f"Seed concluído: {inseridos} curso(s) inserido(s).")


if __name__ == "__main__":
    asyncio.run(main())

"""Popula o banco com os 6 cursos da vitrine (mesmo conteúdo do portal).

Uso (a partir de backend/):
    python -m scripts.seed
ou via Docker:
    docker compose run --rm --entrypoint python backend -m scripts.seed

Idempotente: cursos já existentes (por slug) são ignorados. São dados de
marketing realistas (placeholder) — dá pra editar/excluir depois pelo admin.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Aula, Curso, Modulo, TipoCurso

# Conteúdo de detalhe (descrição, "o que aprende" e módulos/aulas) — o mesmo que
# o portal exibe hoje para todos os cursos. Cada aula é (titulo, "mm:ss").
DESC = (
    "O câmbio automatizado mais comum nas oficinas brasileiras — e o que mais gera "
    "retrabalho quando diagnosticado no chute. Você aprende o método para atacar "
    "atuador, bomba, sangria e calibração com proxxon/scanner, isolando a falha real "
    "antes de abrir."
)
APRENDE = [
    "Sangrar e calibrar o sistema corretamente",
    "Diagnosticar o atuador (motor de embreagem e de marcha)",
    "Ler parâmetros do scanner que apontam a falha real",
    "Identificar desgaste de embreagem x falha hidráulica",
    "Procedimento de autoaprendizagem (PIS) pós-reparo",
    "Montar laudo técnico e orçamento que o cliente aprova",
]
MODULOS = [
    {"titulo": "Como funciona o sistema", "aulas": [
        ("Arquitetura do sistema", "12:40"),
        ("Atuador, bomba e acumulador", "18:05"),
        ("Ferramentas e bancada mínima", "09:30"),
    ]},
    {"titulo": "Diagnóstico na prática", "aulas": [
        ("Lendo o scanner sem medo", "22:10"),
        ("Sangria e pressão do sistema", "19:45"),
        ("Embreagem: desgaste x hidráulica", "16:20"),
    ]},
    {"titulo": "Reparo e atuador", "aulas": [
        ("Desmontagem do atuador", "20:00"),
        ("Troca de embreagem e volante", "24:15"),
        ("Vazamentos e selagem", "17:50"),
    ]},
    {"titulo": "Calibração e entrega", "aulas": [
        ("Autoaprendizagem (PIS)", "14:30"),
        ("Road-test com checklist", "15:10"),
        ("Apresentando o orçamento certo", "11:25"),
    ]},
]

# Cabeçalho próprio de cada curso (vitrine + topo da página de venda).
CURSOS: list[dict] = [
    {"slug": "dualogic", "titulo": "Fiat Dualogic — Diagnóstico e Reparo",
     "tagline": "Punto, Linea, Stilo e Bravo: atuador, sangria e calibração sem chute.",
     "preco": 397, "preco_antigo": 597, "horas": "8h40", "aulas_total": 42,
     "rating": 4.9, "alunos": 1840, "nivel": "Intermediário", "icon": "gauge", "badge_label": "Automatizado", "destaque": True},
    {"slug": "powershift", "titulo": "Ford PowerShift — Embreagem Seca (DCT)",
     "tagline": "Focus e EcoSport: por que a embreagem seca falha e como reparar.",
     "preco": 447, "preco_antigo": 647, "horas": "9h05", "aulas_total": 45,
     "rating": 4.8, "alunos": 1310, "nivel": "Avançado", "icon": "infinity", "badge_label": "Automatizado"},
    {"slug": "imotion", "titulo": "VW iMotion — Fox e SpaceFox",
     "tagline": "Atuador, calibração e as falhas que mais aparecem na bancada.",
     "preco": 347, "preco_antigo": 497, "horas": "6h10", "aulas_total": 31,
     "rating": 4.9, "alunos": 980, "nivel": "Intermediário", "icon": "bolt", "badge_label": "Automatizado"},
    {"slug": "easytronic", "titulo": "GM Easytronic — Meriva e Corsa",
     "tagline": "Domine o automatizado da GM: atuador, sensores e calibração.",
     "preco": 347, "preco_antigo": 497, "horas": "5h50", "aulas_total": 29,
     "rating": 4.7, "alunos": 760, "nivel": "Intermediário", "icon": "gauge", "badge_label": "Automatizado"},
    {"slug": "dsg", "titulo": "DSG DQ200 / DQ250 — VW e Audi",
     "tagline": "Dupla embreagem: mecatrônica, banho de óleo e seca na prática.",
     "preco": 497, "preco_antigo": 747, "horas": "11h20", "aulas_total": 53,
     "rating": 5.0, "alunos": 690, "nivel": "Avançado", "icon": "infinity", "badge_label": "Dupla embreagem"},
    {"slug": "automatico", "titulo": "Câmbio Automático Convencional",
     "tagline": "Hidráulico e eletrônico: pressão, conversor e scanner do zero.",
     "preco": 397, "preco_antigo": 547, "horas": "8h25", "aulas_total": 40,
     "rating": 4.9, "alunos": 2010, "nivel": "Iniciante", "icon": "wrench", "badge_label": "Automático"},
]


def _secs(label: str) -> int:
    m, s = label.split(":")
    return int(m) * 60 + int(s)


async def _seed_curso(session, data: dict, ordem: int) -> bool:
    existe = await session.scalar(select(Curso.id).where(Curso.slug == data["slug"]))
    if existe is not None:
        return False

    curso = Curso(
        slug=data["slug"],
        titulo=data["titulo"],
        descricao=DESC,
        tipo=TipoCurso.avulso,
        preco=data["preco"],
        preco_antigo=data["preco_antigo"],
        validade_dias=365,
        destaque=False,
        ordem=ordem,
        tagline=data["tagline"],
        horas=data["horas"],
        aulas_total=data["aulas_total"],
        rating=data["rating"],
        alunos=data["alunos"],
        nivel=data["nivel"],
        icon=data["icon"],
        badge_label=data["badge_label"],
        aprende=APRENDE,
    )
    for m_idx, mod in enumerate(MODULOS, start=1):
        modulo = Modulo(titulo=mod["titulo"], ordem=m_idx)
        for a_idx, (titulo, dur) in enumerate(mod["aulas"], start=1):
            modulo.aulas.append(Aula(titulo=titulo, duracao_segundos=_secs(dur), ordem=a_idx))
        curso.modulos.append(modulo)

    session.add(curso)
    return True


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, connect_args=settings.db_connect_args)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    inseridos = 0
    async with Session() as session:
        for ordem, data in enumerate(CURSOS, start=1):
            if await _seed_curso(session, data, ordem):
                inseridos += 1
                print(f"  + {data['slug']}")
            else:
                print(f"  = {data['slug']} já existe, ignorado")
        await session.commit()

    await engine.dispose()
    print(f"Seed concluído: {inseridos} curso(s) inserido(s).")


if __name__ == "__main__":
    asyncio.run(main())

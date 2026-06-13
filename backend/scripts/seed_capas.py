"""Gera capas SVG no estilo blueprint da RödelCar para os cursos existentes,
sobe ao Supabase Storage e grava a URL em `cursos.thumbnail_url`.

Uso (com SUPABASE_URL/SUPABASE_SERVICE_KEY no .env):
    docker compose run --rm --entrypoint python backend -m scripts.seed_capas

Idempotente: cada execução cria uma capa nova e atualiza o thumbnail_url.
Passe --so-sem-capa para pular cursos que já têm capa.
"""
from __future__ import annotations

import asyncio
import sys
from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.storage import FORMATOS_SVG, storage_ativo, upload_imagem
from app.models import Curso

# slug → (sistema em destaque, legenda técnica)
SISTEMAS = {
    "dualogic": ("Dualogic", "Fiat · Câmbio automatizado"),
    "powershift": ("PowerShift", "Ford · Dupla embreagem seca"),
    "imotion": ("iMotion", "VW · Câmbio automatizado"),
    "easytronic": ("Easytronic", "GM · Câmbio automatizado"),
    "dsg": ("DSG DQ200/DQ250", "VW · Audi · Dupla embreagem"),
    "automatico": ("Automático", "Conversor de torque"),
}


def _capa_svg(slug: str, titulo: str) -> bytes:
    sistema, legenda = SISTEMAS.get(slug, (titulo[:22], "RödelCar · Câmbios"))
    # variação determinística por slug (rotação e dentes do "cog")
    h = sum(ord(c) for c in slug)
    rot = h % 40 - 20
    dentes = 18 + (h % 8)
    # quebra o nome do sistema em até 2 linhas
    palavras = sistema.split()
    if len(sistema) > 12 and len(palavras) > 1:
        meio = len(palavras) // 2
        l1, l2 = " ".join(palavras[:meio]), " ".join(palavras[meio:])
    else:
        l1, l2 = sistema, ""

    grid = "".join(
        f'<line x1="{x}" y1="0" x2="{x}" y2="450" />' for x in range(0, 801, 26)
    ) + "".join(
        f'<line x1="0" y1="{y}" x2="800" y2="{y}" />' for y in range(0, 451, 26)
    )

    titulo_lines = (
        f'<text x="56" y="250" class="big">{escape(l1)}</text>'
        + (f'<text x="56" y="320" class="big">{escape(l2)}</text>' if l2 else "")
    )
    y_legenda = 320 if l2 else 250
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" font-family="'Segoe UI',Arial,sans-serif">
  <defs>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#E5372B" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#E5372B" stop-opacity="0"/>
    </radialGradient>
    <style>
      .big{{fill:#F2F4F8;font-size:56px;font-weight:800;letter-spacing:-1px}}
      .tag{{fill:#9AA3AF;font-size:15px;letter-spacing:3px;font-family:monospace}}
      .leg{{fill:#C7CDD6;font-size:18px}}
    </style>
  </defs>
  <rect width="800" height="450" fill="#0A0C10"/>
  <g stroke="#FFFFFF" stroke-opacity="0.045" stroke-width="1">{grid}</g>
  <circle cx="700" cy="90" r="300" fill="url(#glow)"/>
  <g transform="translate(605,250) rotate({rot})">
    <circle r="118" fill="none" stroke="#E5372B" stroke-width="11"
            stroke-dasharray="{118 * 2 * 3.14159 / dentes / 2:.1f} {118 * 2 * 3.14159 / dentes / 2:.1f}"/>
    <circle r="86" fill="none" stroke="#E5372B" stroke-opacity="0.45" stroke-width="3"/>
    <circle r="44" fill="#E5372B" fill-opacity="0.12" stroke="#E5372B" stroke-width="2"/>
    <circle r="9" fill="#E5372B"/>
  </g>
  <g transform="translate(470,120) rotate({-rot})">
    <circle r="48" fill="none" stroke="#E5372B" stroke-opacity="0.6" stroke-width="6"
            stroke-dasharray="9 9"/>
    <circle r="18" fill="none" stroke="#E5372B" stroke-opacity="0.5" stroke-width="2"/>
  </g>
  <text x="56" y="150" class="tag">// RÖDELCAR · CÂMBIOS</text>
  {titulo_lines}
  <text x="56" y="{y_legenda + 36}" class="leg">{escape(legenda)}</text>
</svg>""".encode("utf-8")


async def main() -> None:
    so_sem_capa = "--so-sem-capa" in sys.argv
    if not storage_ativo():
        print("! Supabase Storage não configurado (SUPABASE_URL/SUPABASE_SERVICE_KEY).")
        return
    engine = create_async_engine(settings.DATABASE_URL, connect_args=settings.db_connect_args)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        cursos = (await s.execute(select(Curso))).scalars().all()
        for curso in cursos:
            if so_sem_capa and curso.thumbnail_url:
                print(f"= {curso.slug}: já tem capa, pulando.")
                continue
            svg = _capa_svg(curso.slug, curso.titulo)
            url = await upload_imagem(svg, "image/svg+xml", "cursos", formatos=FORMATOS_SVG)
            curso.thumbnail_url = url
            await s.commit()
            print(f"+ {curso.slug}: {url}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

"""Dispara AGORA a atualização de views/likes/duração dos vídeos da prova social
(e esconde os indisponíveis), sem esperar o cron diário das 06:40 UTC.

Rodar (modo módulo, p/ o pacote `app` ficar no path):
    docker compose run --rm --entrypoint python backend -m scripts.atualizar_videos
"""
import asyncio

from app.core.scheduler import _job_atualizar_videos


if __name__ == "__main__":
    asyncio.run(_job_atualizar_videos())
    print("Atualização de vídeos concluída (ver log acima).")

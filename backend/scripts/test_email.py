"""Testa o envio de e-mail via SMTP, mostrando o erro REAL (não engole exceção).

Uso (manda para o próprio remetente):
    docker compose run --rm --entrypoint python backend -m scripts.test_email

Ou para um destino específico:
    docker compose run --rm --entrypoint python backend -m scripts.test_email destino@exemplo.com
"""
from __future__ import annotations

import asyncio
import sys

import aiosmtplib
from email.message import EmailMessage

from app.core.config import settings


async def main() -> None:
    para = sys.argv[1] if len(sys.argv) > 1 else settings.EMAIL_FROM

    print("── Config SMTP ────────────────────────────")
    print(f"  SMTP_HOST = {settings.SMTP_HOST!r}")
    print(f"  SMTP_PORT = {settings.SMTP_PORT}")
    print(f"  SMTP_USER = {settings.SMTP_USER!r}")
    print(f"  SMTP_PASSWORD definido? {'sim' if settings.SMTP_PASSWORD else 'NÃO'}")
    print(f"  EMAIL_FROM = {settings.EMAIL_FROM!r}")
    print(f"  destino    = {para!r}")
    print("───────────────────────────────────────────")

    if not settings.SMTP_HOST:
        print("ERRO: SMTP_HOST vazio — confira o .env e reinicie o backend.")
        return

    em = EmailMessage()
    em["From"] = settings.EMAIL_FROM
    em["To"] = para
    em["Subject"] = "Teste SMTP — RödelCar"
    em.add_alternative(
        "<p>Funcionou! 🎉 SMTP da RödelCar configurado corretamente.</p>",
        subtype="html",
    )

    use_tls = settings.SMTP_PORT == 465
    async with aiosmtplib.SMTP(
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        use_tls=use_tls,
        start_tls=not use_tls,
    ) as smtp:
        if settings.SMTP_USER:
            await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        await smtp.send_message(em)

    print("✅ E-mail enviado com sucesso. Confira a caixa de entrada (e o spam).")


if __name__ == "__main__":
    asyncio.run(main())

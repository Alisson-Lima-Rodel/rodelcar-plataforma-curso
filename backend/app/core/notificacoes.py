"""Envio de notificações de vigência: e-mail (SMTP) e WhatsApp (multi-provider)."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

import aiosmtplib
import httpx

from app.core.config import settings
from app.models import TipoNotificacao

logger = logging.getLogger(__name__)


@dataclass
class MensagemNotificacao:
    aluno_id: uuid.UUID  # usado nos logs (em vez de e-mail/telefone — LGPD)
    aluno_nome: str
    aluno_email: str
    aluno_telefone: str | None
    tipo: TipoNotificacao
    marco: str          # "15d" | "7d" | "1d" | "expirado"
    curso_titulo: str
    data_expiracao: datetime


# ── Templates ─────────────────────────────────────────────────────────────────

def _primeiro_nome(nome_completo: str) -> str:
    return nome_completo.split()[0]


def _build_email_subject(msg: MensagemNotificacao) -> str:
    if msg.tipo == TipoNotificacao.vigencia_expirada:
        return f"Seu acesso ao {msg.curso_titulo} expirou — renove agora"
    dias = msg.marco.replace("d", "")
    return f"⚠️ Seu acesso ao {msg.curso_titulo} expira em {dias} dias"


def _build_email_body(msg: MensagemNotificacao) -> str:
    nome = _primeiro_nome(msg.aluno_nome)
    data_fmt = msg.data_expiracao.strftime("%d/%m/%Y")
    url = settings.renovacao_url

    if msg.tipo == TipoNotificacao.vigencia_expirada:
        return f"""
<p>Olá, <strong>{nome}</strong>!</p>
<p>Seu acesso ao curso <strong>{msg.curso_titulo}</strong> expirou em {data_fmt}.</p>
<p>Renove agora com condições especiais e continue sua capacitação em câmbios automáticos:</p>
<p style="margin:24px 0">
  <a href="{url}" style="background:#f97316;color:#fff;padding:12px 28px;
     border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">
    Renovar acesso agora
  </a>
</p>
<p style="color:#888;font-size:12px;">
  RödelCar Câmbios — Especialistas em transmissões automáticas
</p>
"""

    dias = msg.marco.replace("d", "")
    return f"""
<p>Olá, <strong>{nome}</strong>!</p>
<p>Seu acesso ao curso <strong>{msg.curso_titulo}</strong> expira em
   <strong>{dias} dias</strong> ({data_fmt}).</p>
<p>Renove antes de perder o acesso e mantenha seu aprendizado em dia:</p>
<p style="margin:24px 0">
  <a href="{url}" style="background:#f97316;color:#fff;padding:12px 28px;
     border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">
    Renovar agora
  </a>
</p>
<p style="color:#888;font-size:12px;">
  RödelCar Câmbios — Especialistas em transmissões automáticas
</p>
"""


def _build_wa_text(msg: MensagemNotificacao) -> str:
    nome = _primeiro_nome(msg.aluno_nome)
    data_fmt = msg.data_expiracao.strftime("%d/%m/%Y")
    url = settings.renovacao_url

    if msg.tipo == TipoNotificacao.vigencia_expirada:
        return (
            f"Olá {nome}! 👋\n\n"
            f"Seu acesso ao curso *{msg.curso_titulo}* expirou em {data_fmt}.\n\n"
            f"Renove agora com condições especiais:\n{url}"
        )

    dias = msg.marco.replace("d", "")
    return (
        f"Olá {nome}! 👋\n\n"
        f"⚠️ Seu acesso ao curso *{msg.curso_titulo}* expira em *{dias} dias* ({data_fmt}).\n\n"
        f"Renove antes de perder o acesso:\n{url}"
    )


# ── Envio de e-mail ────────────────────────────────────────────────────────────

async def enviar_email_bruto(
    para: str, assunto: str, corpo_html: str, *, log_ref: str = "?"
) -> str | None:
    """Envia um e-mail HTML qualquer via SMTP. Base reutilizável (vigência,
    boas-vindas, certificado…). `log_ref` aparece nos logs no lugar do e-mail
    (LGPD). Retorna identificador ou None em falha/ausência de config."""
    if settings.NOTIFICACOES_FAKE:
        logger.info("[FAKE EMAIL] ref=%s assunto=%r", log_ref, assunto)
        return f"fake-email-{uuid.uuid4()}"

    if not settings.SMTP_HOST:
        logger.debug("SMTP_HOST não configurado — e-mail ignorado (ref=%s)", log_ref)
        return None

    em = EmailMessage()
    em["From"] = settings.EMAIL_FROM
    em["To"] = para
    em["Subject"] = assunto
    em.add_alternative(corpo_html, subtype="html")

    use_tls = settings.SMTP_PORT == 465
    try:
        async with aiosmtplib.SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=use_tls,
        ) as smtp:
            if not use_tls:
                await smtp.starttls()
            if settings.SMTP_USER:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            await smtp.send_message(em)
        return f"smtp-{uuid.uuid4()}"
    except Exception:
        logger.exception("Falha ao enviar e-mail (ref=%s)", log_ref)
        return None


async def enviar_email(msg: MensagemNotificacao) -> str | None:
    """Envia o e-mail de vigência (montado a partir de MensagemNotificacao)."""
    return await enviar_email_bruto(
        msg.aluno_email,
        _build_email_subject(msg),
        _build_email_body(msg),
        log_ref=str(msg.aluno_id),
    )


# ── Provedores de WhatsApp ─────────────────────────────────────────────────────

def _normalizar_telefone(tel: str) -> str:
    """Remove formatação; mantém apenas dígitos (sem '+')."""
    return tel.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").lstrip("+")


async def _wa_meta(telefone: str, texto: str) -> str:
    url = f"https://graph.facebook.com/v19.0/{settings.WA_META_PHONE_ID}/messages"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "to": _normalizar_telefone(telefone),
                "type": "text",
                "text": {"body": texto},
            },
            headers={"Authorization": f"Bearer {settings.WA_META_TOKEN}"},
        )
        r.raise_for_status()
        return r.json()["messages"][0]["id"]


async def _wa_twilio(telefone: str, texto: str) -> str:
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.WA_TWILIO_ACCOUNT_SID}/Messages.json"
    )
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            url,
            data={
                "From": settings.WA_TWILIO_FROM,
                "To": f"whatsapp:{telefone}",
                "Body": texto,
            },
            auth=(settings.WA_TWILIO_ACCOUNT_SID, settings.WA_TWILIO_AUTH_TOKEN),
        )
        r.raise_for_status()
        return r.json()["sid"]


async def _wa_zapi(telefone: str, texto: str) -> str:
    url = (
        f"https://api.z-api.io/instances/{settings.WA_ZAPI_INSTANCE_ID}"
        f"/token/{settings.WA_ZAPI_TOKEN}/send-text"
    )
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            url,
            json={"phone": _normalizar_telefone(telefone), "message": texto},
            headers={"Client-Token": settings.WA_ZAPI_CLIENT_TOKEN},
        )
        r.raise_for_status()
        data = r.json()
        return data.get("zaapId") or data.get("id") or f"zapi-{uuid.uuid4()}"


async def enviar_whatsapp_texto(
    telefone: str | None, texto: str, *, log_ref: str = "?"
) -> str | None:
    """Envia um texto livre por WhatsApp via provider configurado.

    Base reutilizável (vigência, certificado, etc). `log_ref` aparece nos logs no
    lugar do telefone (LGPD — nunca logar PII). Retorna provedor_msg_id ou None.
    """
    if not telefone:
        logger.debug("Telefone ausente (ref=%s) — WhatsApp ignorado", log_ref)
        return None

    if settings.NOTIFICACOES_FAKE:
        # Não loga telefone nem o texto da mensagem (PII/conteúdo) — só o ref.
        logger.info("[FAKE WHATSAPP] ref=%s", log_ref)
        return f"fake-wa-{uuid.uuid4()}"

    if not settings.WA_PROVIDER:
        logger.debug("WhatsApp não configurado (WA_PROVIDER) — ref=%s", log_ref)
        return None

    provider = settings.WA_PROVIDER.lower()
    try:
        if provider == "meta":
            return await _wa_meta(telefone, texto)
        if provider == "twilio":
            return await _wa_twilio(telefone, texto)
        if provider == "zapi":
            return await _wa_zapi(telefone, texto)
        logger.warning("WA_PROVIDER desconhecido: %s", settings.WA_PROVIDER)
        return None
    except Exception:
        logger.exception(
            "Falha ao enviar WhatsApp (ref=%s) via %s", log_ref, settings.WA_PROVIDER
        )
        return None


async def enviar_whatsapp(msg: MensagemNotificacao) -> str | None:
    """Envia o WhatsApp de vigência (texto montado a partir de MensagemNotificacao)."""
    return await enviar_whatsapp_texto(
        msg.aluno_telefone, _build_wa_text(msg), log_ref=str(msg.aluno_id)
    )

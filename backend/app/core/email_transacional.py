"""Conteúdo dos e-mails transacionais (pós-compra, certificado).

Cada builder devolve `(assunto, corpo_html)` pronto para `enviar_email_bruto`.
Valores dinâmicos (nome do aluno, título do curso) são escapados com
`html.escape` — um nome com `<...>` não injeta HTML no e-mail.
"""

from html import escape

from app.core.config import settings


def _primeiro_nome(nome: str | None) -> str:
    return nome.split()[0] if nome and nome.split() else "aluno(a)"


def _layout(saudacao: str, paragrafos: str, cta_label: str, cta_url: str) -> str:
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;color:#13161c;max-width:560px;line-height:1.55">
  <p style="font-size:1.1rem;margin:0 0 14px"><strong>{saudacao}</strong></p>
  {paragrafos}
  <p style="margin:26px 0">
    <a href="{cta_url}" style="background:#E5372B;color:#fff;padding:12px 28px;
       border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">{cta_label}</a>
  </p>
  <p style="color:#888;font-size:12px;margin-top:28px">
    RödelCar Câmbios — Especialistas em câmbios automáticos e automatizados · Canoas-RS
  </p>
</div>"""


def email_compra_avulsa(nome: str | None, curso_titulo: str) -> tuple[str, str]:
    curso = escape(curso_titulo)
    assunto = f"✅ Compra confirmada — {curso_titulo}"
    corpo = _layout(
        f"Bem-vindo(a), {escape(_primeiro_nome(nome))}!",
        f"<p>Seu pagamento foi confirmado e o acesso ao curso "
        f"<strong>{curso}</strong> já está liberado. Bons estudos! 🔧</p>",
        "Acessar meu curso",
        f"{settings.PORTAL_URL.rstrip('/')}/painel",
    )
    return assunto, corpo


def email_assinatura(nome: str | None) -> tuple[str, str]:
    assunto = "✅ Assinatura RödelCar confirmada — acesso total liberado"
    corpo = _layout(
        f"Bem-vindo(a), {escape(_primeiro_nome(nome))}!",
        "<p>Sua assinatura foi confirmada. Você agora tem acesso a "
        "<strong>todos os cursos do catálogo</strong> enquanto a assinatura "
        "estiver ativa. Aproveite!</p>",
        "Acessar a plataforma",
        f"{settings.PORTAL_URL.rstrip('/')}/painel",
    )
    return assunto, corpo


def email_reset_senha(nome: str | None, reset_url: str) -> tuple[str, str]:
    assunto = "🔑 Redefinição de senha — RödelCar"
    corpo = _layout(
        f"Olá, {escape(_primeiro_nome(nome))}!",
        "<p>Recebemos um pedido para redefinir a sua senha na RödelCar. "
        "Clique no botão abaixo para criar uma nova senha — o link é válido por "
        "<strong>24 horas</strong>.</p>"
        '<p style="color:#888;font-size:13px">Se você não solicitou, ignore '
        "este e-mail: sua senha atual continua valendo.</p>",
        "Redefinir minha senha",
        reset_url,
    )
    return assunto, corpo


def email_certificado(
    nome: str | None, curso_titulo: str, verify_url: str
) -> tuple[str, str]:
    curso = escape(curso_titulo)
    assunto = f"🎓 Seu certificado — {curso_titulo}"
    corpo = _layout(
        f"Parabéns, {escape(_primeiro_nome(nome))}!",
        f"<p>Você concluiu o curso <strong>{curso}</strong> e seu certificado "
        f"já está disponível. Baixe o PDF no painel e verifique a autenticidade "
        f"a qualquer momento pelo link:</p>"
        f'<p style="font-size:0.9rem"><a href="{escape(verify_url)}">{escape(verify_url)}</a></p>',
        "Ver meu certificado",
        f"{settings.PORTAL_URL.rstrip('/')}/painel",
    )
    return assunto, corpo

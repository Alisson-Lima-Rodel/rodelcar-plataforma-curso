"""Gera o PDF do certificado de conclusão (reportlab, sem dependência nativa).

Helvetica embutida já cobre os acentos do pt-BR (Latin-1), então não é preciso
empacotar fonte. Layout A4 paisagem, identidade da marca (vermelho #E5372B).
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

_VERMELHO = HexColor("#E5372B")
_TINTA = HexColor("#13161c")
_CINZA = HexColor("#6b7280")
_BORDA = HexColor("#e5e7eb")

_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _data_extenso(dt: datetime) -> str:
    return f"{dt.day} de {_MESES[dt.month - 1]} de {dt.year}"


def gerar_pdf_certificado(
    *,
    aluno_nome: str,
    curso_titulo: str,
    codigo: str,
    emitido_em: datetime,
    horas: str | None,
    verify_url: str,
) -> bytes:
    """Devolve os bytes do PDF do certificado."""
    buf = BytesIO()
    largura, altura = landscape(A4)
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(f"Certificado — {curso_titulo}")

    # Moldura dupla
    c.setStrokeColor(_BORDA)
    c.setLineWidth(1)
    c.rect(10 * mm, 10 * mm, largura - 20 * mm, altura - 20 * mm)
    c.setStrokeColor(_VERMELHO)
    c.setLineWidth(3)
    c.rect(13 * mm, 13 * mm, largura - 26 * mm, altura - 26 * mm)

    centro = largura / 2

    # Marca
    c.setFillColor(_TINTA)
    c.setFont("Helvetica-BoldOblique", 26)
    c.drawCentredString(centro, altura - 38 * mm, "RodelCar")
    c.setFillColor(_CINZA)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(
        centro, altura - 45 * mm, "CÂMBIOS AUTOMÁTICOS E AUTOMATIZADOS"
    )

    # Faixa vermelha
    c.setStrokeColor(_VERMELHO)
    c.setLineWidth(2)
    c.line(centro - 28 * mm, altura - 50 * mm, centro + 28 * mm, altura - 50 * mm)

    # Título
    c.setFillColor(_CINZA)
    c.setFont("Helvetica", 12)
    c.drawCentredString(centro, altura - 64 * mm, "CERTIFICADO DE CONCLUSÃO")

    # Nome do aluno
    c.setFillColor(_TINTA)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(centro, altura - 82 * mm, aluno_nome)

    # Texto de concessão
    carga = f" — carga horária de {horas}" if horas else ""
    c.setFillColor(_CINZA)
    c.setFont("Helvetica", 12)
    c.drawCentredString(
        centro, altura - 94 * mm, "concluiu com aproveitamento o curso"
    )
    c.setFillColor(_VERMELHO)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(centro, altura - 104 * mm, curso_titulo)
    if carga:
        c.setFillColor(_CINZA)
        c.setFont("Helvetica", 11)
        c.drawCentredString(centro, altura - 112 * mm, carga.lstrip(" —"))

    # Rodapé: data + código + verificação
    base_y = 30 * mm
    c.setFillColor(_TINTA)
    c.setFont("Helvetica", 10)
    c.drawCentredString(centro, base_y + 14 * mm, _data_extenso(emitido_em))
    c.setFillColor(_CINZA)
    c.setFont("Helvetica", 9)
    c.drawCentredString(centro, base_y + 7 * mm, f"Código de verificação: {codigo}")
    c.setFillColor(_VERMELHO)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(centro, base_y, f"Verifique a autenticidade em {verify_url}")

    c.showPage()
    c.save()
    return buf.getvalue()

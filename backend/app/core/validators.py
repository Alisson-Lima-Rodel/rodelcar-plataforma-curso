"""Validadores compartilhados de boundary (Pydantic field_validators).

Centraliza a normalização de telefone BR usada no cadastro do aluno (público) e
no CRUD de alunos do admin — mesma regra, uma fonte só.
"""
from __future__ import annotations


def telefone_br(v: str | None) -> str | None:
    """Normaliza e valida telefone BR: guarda só dígitos (DDD + número, 10–11).

    Aceita máscara/"+55" na entrada (descarta o 55 do país se vier com 12–13
    dígitos). Vazio/None vira None. Inválido → ValueError (vira 422). O valor
    normalizado é o que alimenta o link `wa.me/55...`.
    """
    if v is None:
        return None
    digitos = "".join(c for c in v if c.isdigit())
    if not digitos:
        return None
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) not in (10, 11):
        raise ValueError("Telefone deve ter DDD + número (10 ou 11 dígitos).")
    return digitos


def telefone_br_obrigatorio(v: str | None) -> str:
    """Como `telefone_br`, mas OBRIGATÓRIO: recusa vazio/None (cadastro do aluno
    exige WhatsApp). Devolve sempre os dígitos normalizados."""
    out = telefone_br(v)
    if out is None:
        raise ValueError("Informe um WhatsApp válido (DDD + número).")
    return out

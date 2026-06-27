import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import telefone_br_obrigatorio
from app.models import StatusLead


# ── POST /leads (público — captação/contato) ──────────────────────────────────
class LeadCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    telefone: str = Field(min_length=8, max_length=40)
    email: EmailStr | None = None
    tipo_servico: str = Field(default="avaliacao_cambio", max_length=80)
    mensagem: str | None = Field(default=None, max_length=2000)
    origem: str | None = Field(default=None, max_length=80)

    # Valida (DDD + número, BR) e grava SÓ dígitos — sem máscara/hífen/parênteses.
    # Mesmo normalizador do cadastro do aluno e do CRUD admin.
    _valida_tel = field_validator("telefone")(telefone_br_obrigatorio)


class LeadCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: StatusLead

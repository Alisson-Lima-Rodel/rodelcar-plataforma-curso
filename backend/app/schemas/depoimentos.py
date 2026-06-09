import uuid

from pydantic import BaseModel, ConfigDict


class DepoimentoPublico(BaseModel):
    """Depoimento aprovado, exposto na prova social pública (sem status/ordem)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    papel: str | None = None
    estrelas: int
    texto: str

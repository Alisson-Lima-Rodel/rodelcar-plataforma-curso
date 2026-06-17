import uuid

from pydantic import BaseModel, ConfigDict


class MaterialResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    url_pdf: str


class ProgressoAula(BaseModel):
    concluida: bool
    percentual: float
    # Segundo onde o aluno parou — o player dá `seek` aqui ao reabrir (resume).
    posicao_segundos: int = 0


class AulaDetail(BaseModel):
    id: uuid.UUID
    titulo: str
    modulo_id: uuid.UUID
    panda_video_id: str | None
    duracao_segundos: int
    materiais: list[MaterialResumo]
    progresso: ProgressoAula

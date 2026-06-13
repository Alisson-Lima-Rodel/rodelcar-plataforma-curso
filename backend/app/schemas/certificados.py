import uuid
from datetime import datetime

from pydantic import BaseModel


class CertificadoResponse(BaseModel):
    id: uuid.UUID
    codigo_verificacao: str
    emitido_em: datetime


class CertificadoVerificacao(BaseModel):
    valido: bool
    aluno_nome: str
    curso: str
    emitido_em: datetime


class CertificadoEnvioResponse(BaseModel):
    enviado: bool

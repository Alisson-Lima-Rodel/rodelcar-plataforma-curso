import uuid

from pydantic import BaseModel, Field


# ── Aluno: ver e responder o quiz ─────────────────────────────────────────────
class AlternativaPublica(BaseModel):
    """SEM o campo `correta` — nunca vaza o gabarito para o aluno."""
    id: uuid.UUID
    texto: str


class QuestaoPublica(BaseModel):
    id: uuid.UUID
    enunciado: str
    alternativas: list[AlternativaPublica]


class QuizPublico(BaseModel):
    id: uuid.UUID
    titulo: str
    nota_corte: float
    questoes: list[QuestaoPublica]
    aprovado: bool          # o aluno já passou alguma vez?
    melhor_nota: float | None = None


class RespostaItem(BaseModel):
    questao_id: uuid.UUID
    alternativa_id: uuid.UUID


class TentativaInput(BaseModel):
    respostas: list[RespostaItem]


class TentativaResultado(BaseModel):
    nota: float
    aprovado: bool
    corretas: int
    total: int


# ── Admin: editar o quiz (com gabarito) ───────────────────────────────────────
class AlternativaAdmin(BaseModel):
    texto: str = Field(min_length=1, max_length=500)
    correta: bool = False


class QuestaoAdmin(BaseModel):
    enunciado: str = Field(min_length=1, max_length=2000)
    alternativas: list[AlternativaAdmin] = Field(min_length=2, max_length=6)


class QuizUpsert(BaseModel):
    titulo: str = Field(min_length=2, max_length=200)
    nota_corte: float = Field(default=70, ge=1, le=100)
    ativo: bool = True
    questoes: list[QuestaoAdmin] = Field(default_factory=list, max_length=50)


class AlternativaAdminOut(AlternativaAdmin):
    id: uuid.UUID


class QuestaoAdminOut(BaseModel):
    id: uuid.UUID
    enunciado: str
    alternativas: list[AlternativaAdminOut]


class QuizAdmin(BaseModel):
    id: uuid.UUID
    modulo_id: uuid.UUID
    titulo: str
    nota_corte: float
    ativo: bool
    questoes: list[QuestaoAdminOut]

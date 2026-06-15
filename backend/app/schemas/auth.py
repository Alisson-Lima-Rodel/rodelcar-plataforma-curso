import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RegisterRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    # max 72: o bcrypt trunca silenciosamente em 72 bytes — alinhar o limite evita
    # que parte da senha seja ignorada sem o usuário saber. min 8: piso razoável.
    senha: str = Field(min_length=8, max_length=72)
    # Indique-e-ganhe: código de quem indicou (opcional; vem do ?ref= no cadastro).
    codigo_indicacao: str | None = Field(default=None, max_length=20)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    matriculas_ativas: int

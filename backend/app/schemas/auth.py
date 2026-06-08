import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RegisterRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=128)


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

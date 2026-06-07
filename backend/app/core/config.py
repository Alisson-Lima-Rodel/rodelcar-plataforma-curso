from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de placeholder que JAMAIS podem valer em produção.
_INSECURE_DEFAULTS = {
    "JWT_SECRET": {"dev-secret", "change-this-to-a-strong-random-secret-min-32-chars"},
    "INTERNAL_TOKEN": {"", "change-to-a-strong-random-secret", "dev-internal-token"},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://rodelcar:rodelcar@localhost:5432/rodelcar"
    JWT_SECRET: str = "dev-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    RODELCAR_FERNET_KEY: str = ""
    INTERNAL_TOKEN: str = ""
    ENVIRONMENT: str = "development"

    # Origens liberadas no CORS (lista separada por vírgula). Em produção,
    # apontar para o domínio do front na Vercel.
    CORS_ORIGINS: str = "http://localhost:3000"
    # Limite por IP nas rotas públicas (formato slowapi/limits).
    RATE_LIMIT_PUBLIC: str = "120/minute"
    # Teto estrito para autenticação (anti brute-force). Override por env.
    RATE_LIMIT_AUTH: str = "5/minute"
    # Storage do rate limiter. Vazio = memória (só serve p/ 1 processo/instância).
    # Em produção multi-instância, aponte para Redis: redis://host:6379/0
    RATELIMIT_STORAGE_URI: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @model_validator(mode="after")
    def _fail_fast_em_producao(self) -> "Settings":
        """Em produção, recusa subir com segredo fraco/ausente.

        Sem isso, uma env esquecida no deploy faz a API bootar com `dev-secret`
        (qualquer um forja JWT) ou sem chave Fernet (CPF fica ilegível). Melhor
        falhar no startup do que rodar inseguro na nuvem.
        """
        if not self.is_production:
            return self

        problemas: list[str] = []
        if self.JWT_SECRET in _INSECURE_DEFAULTS["JWT_SECRET"] or len(self.JWT_SECRET) < 32:
            problemas.append("JWT_SECRET ausente/fraco (use >= 32 chars aleatórios)")
        if not self.RODELCAR_FERNET_KEY:
            problemas.append("RODELCAR_FERNET_KEY ausente (CPF cifrado exige chave fixa)")
        if self.INTERNAL_TOKEN in _INSECURE_DEFAULTS["INTERNAL_TOKEN"]:
            problemas.append("INTERNAL_TOKEN ausente/placeholder")
        if "rodelcar:rodelcar@" in self.DATABASE_URL:
            problemas.append("DATABASE_URL usa credenciais default (rodelcar:rodelcar)")

        if problemas:
            raise ValueError(
                "Configuração insegura para ENVIRONMENT=production:\n  - "
                + "\n  - ".join(problemas)
            )
        return self


settings = Settings()

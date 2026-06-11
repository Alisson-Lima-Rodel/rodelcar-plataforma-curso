from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de placeholder que JAMAIS podem valer em produção. Inclui o default do
# docker-compose.yml (`dev-jwt-secret-change-in-production`): ele tem >=32 chars e
# passaria pela checagem de tamanho, então precisa ser barrado pelo nome — senão a
# API subiria em produção com uma chave de assinatura JWT pública no repositório.
_INSECURE_DEFAULTS = {
    "JWT_SECRET": {
        "dev-secret",
        "change-this-to-a-strong-random-secret-min-32-chars",
        "dev-jwt-secret-change-in-production",
    },
    "INTERNAL_TOKEN": {"", "change-to-a-strong-random-secret", "dev-internal-token"},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://rodelcar:rodelcar@localhost:5432/rodelcar"
    # Força TLS no driver. Vazio = detecta pelo host (.supabase.co exige SSL).
    # Defina "require"/"verify-full" para forçar manualmente.
    DATABASE_SSL: str = ""
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
    # Nº de workers do uvicorn (espelha o entrypoint.sh, default 2 em produção).
    # Com >1 worker e sem RATELIMIT_STORAGE_URI o teto anti brute-force conta por
    # processo (vira N×); o fail-fast de produção recusa subir nessa combinação.
    WEB_CONCURRENCY: int = 2

    # Modo fake: renderiza e loga as notificações em vez de enviar (dev/testes).
    # Não dispara e-mail/WhatsApp real, mas exercita todo o pipeline (status,
    # idempotência). Mantenha False em produção.
    NOTIFICACOES_FAKE: bool = False

    # ── Notificações — E-mail (SMTP) ──────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@rodelcar.com.br"

    # ── Notificações — WhatsApp (WA_PROVIDER: meta | twilio | zapi | "") ──────
    WA_PROVIDER: str = ""
    # Meta Cloud API
    WA_META_TOKEN: str = ""
    WA_META_PHONE_ID: str = ""
    WA_META_APP_SECRET: str = ""   # assina webhook (X-Hub-Signature-256)
    WA_META_VERIFY_TOKEN: str = "" # desafio do handshake GET
    # Twilio
    WA_TWILIO_ACCOUNT_SID: str = ""
    WA_TWILIO_AUTH_TOKEN: str = ""
    WA_TWILIO_FROM: str = "whatsapp:+14155238886"
    # Z-API
    WA_ZAPI_INSTANCE_ID: str = ""
    WA_ZAPI_TOKEN: str = ""
    WA_ZAPI_CLIENT_TOKEN: str = ""

    # URL de renovação usada nas mensagens de vigência
    RENOVACAO_URL: str = "https://rodelcar.com.br"

    # ── Pagamentos — Stripe ───────────────────────────────────────────────────
    # Chave secreta da API (sk_test_... / sk_live_...). Usada só no checkout.
    STRIPE_SECRET_KEY: str = ""
    # Segredo de assinatura do endpoint de webhook (whsec_...). A validação da
    # assinatura só é exigida quando setado (igual ao WA_META_APP_SECRET).
    STRIPE_WEBHOOK_SECRET: str = ""
    # Para onde a Stripe redireciona após o checkout hospedado.
    STRIPE_SUCCESS_URL: str = "http://localhost:3000/sucesso"
    STRIPE_CANCEL_URL: str = "http://localhost:3000/checkout"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @property
    def db_connect_args(self) -> dict:
        """connect_args do asyncpg. Supabase/Postgres gerenciado exige TLS e o
        asyncpg não ativa SSL sozinho — força aqui quando o host é Supabase ou
        quando DATABASE_SSL pede explicitamente."""
        forced = self.DATABASE_SSL.strip().lower()
        if "supabase.co" in self.DATABASE_URL or forced in {"require", "verify-ca", "verify-full", "true", "1"}:
            mode = forced if forced in {"require", "verify-ca", "verify-full"} else "require"
            return {"ssl": mode}
        return {}

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
        if "://postgres:" in self.DATABASE_URL:
            problemas.append("DATABASE_URL usa o superusuário 'postgres' (use um papel dedicado, não-root)")
        if self.STRIPE_SECRET_KEY and not self.STRIPE_WEBHOOK_SECRET:
            problemas.append("STRIPE_WEBHOOK_SECRET ausente (Stripe ativo → webhook ficaria fail-open)")
        if self.WEB_CONCURRENCY > 1 and not self.RATELIMIT_STORAGE_URI:
            problemas.append(
                "RATELIMIT_STORAGE_URI ausente com WEB_CONCURRENCY>1 (rate limit por "
                "processo → teto anti brute-force multiplicado; use redis://...)"
            )
        if "*" in self.cors_origins_list:
            problemas.append("CORS_ORIGINS contém '*' (use os domínios explícitos do front)")
        if self.WA_PROVIDER == "meta" and not self.WA_META_APP_SECRET:
            problemas.append("WA_META_APP_SECRET ausente (webhook do WhatsApp ficaria sem assinatura)")

        if problemas:
            raise ValueError(
                "Configuração insegura para ENVIRONMENT=production:\n  - "
                + "\n  - ".join(problemas)
            )
        return self


settings = Settings()

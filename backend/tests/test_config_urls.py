"""Consolidação das URLs públicas em PORTAL_URL + fail-fast de produção.

O domínio da plataforma é FONTE ÚNICA: o retorno do Stripe (success/cancel), os
links de certificado/e-mail e a renovação derivam de PORTAL_URL. Estes testes
travam (1) a derivação correta, (2) que um override explícito vence e (3) que o
boot de produção recusa um PORTAL_URL inseguro (vazio, localhost ou sem HTTPS) —
era a causa do checkout "voltar" para o domínio errado.
"""

import pytest

from app.core.config import Settings

# Base mínima de produção que passa por TODOS os outros checks de fail-fast,
# para isolar exatamente o efeito do PORTAL_URL.
_PROD_OK = dict(
    ENVIRONMENT="production",
    JWT_SECRET="x" * 40,
    RODELCAR_FERNET_KEY="k",
    INTERNAL_TOKEN="tok",
    DATABASE_URL="postgresql+asyncpg://u:p@db.ref.supabase.co:5432/postgres",
    CORS_ORIGINS="https://app.exemplo.com.br",
    WEB_CONCURRENCY=1,
)


def _settings(**over) -> Settings:
    # _env_file=None: ignora o .env do host para o teste ser determinístico.
    return Settings(_env_file=None, **over)


def _prod(**over) -> Settings:
    return _settings(**{**_PROD_OK, **over})


class TestDerivacaoUrls:
    def test_deriva_success_cancel_renovacao_de_portal(self):
        s = _settings(
            PORTAL_URL="http://localhost:3000",
            STRIPE_SUCCESS_URL="",
            STRIPE_CANCEL_URL="",
            RENOVACAO_URL="",
        )
        assert s.stripe_success_url == "http://localhost:3000/sucesso"
        assert s.stripe_cancel_url == "http://localhost:3000/"
        assert s.renovacao_url == "http://localhost:3000"

    def test_normaliza_barra_final_de_portal(self):
        s = _settings(PORTAL_URL="https://app.exemplo.com.br/")
        assert s.stripe_success_url == "https://app.exemplo.com.br/sucesso"
        assert s.renovacao_url == "https://app.exemplo.com.br"

    def test_override_explicito_vence_derivacao(self):
        s = _settings(
            PORTAL_URL="https://app.exemplo.com.br",
            STRIPE_CANCEL_URL="https://checkout.outro-host/voltar",
            RENOVACAO_URL="https://promo.exemplo.com.br/renovar",
        )
        assert s.stripe_cancel_url == "https://checkout.outro-host/voltar"
        assert s.renovacao_url == "https://promo.exemplo.com.br/renovar"


class TestFailFastPortalUrl:
    @pytest.mark.parametrize(
        "portal",
        [
            "",                          # sem host → URLs quebradas
            "http://localhost:3000",     # domínio errado vaza no retorno do Stripe
            "http://127.0.0.1:3000",
            "http://0.0.0.0:3000",
            "http://[::1]:3000",
            "http://app.exemplo.com.br",  # produção sem TLS
        ],
    )
    def test_producao_recusa_portal_inseguro(self, portal):
        with pytest.raises(ValueError, match="PORTAL_URL"):
            _prod(PORTAL_URL=portal)

    def test_producao_aceita_dominio_https(self):
        s = _prod(PORTAL_URL="https://app.exemplo.com.br")
        assert s.stripe_success_url == "https://app.exemplo.com.br/sucesso"
        assert s.stripe_cancel_url == "https://app.exemplo.com.br/"

    def test_dev_nao_exige_https(self):
        # Fora de produção o default localhost continua válido (sem fail-fast).
        s = _settings(ENVIRONMENT="development", PORTAL_URL="http://localhost:3000")
        assert s.is_production is False
        assert s.stripe_success_url == "http://localhost:3000/sucesso"

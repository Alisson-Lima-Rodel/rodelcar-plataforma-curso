import uuid

from pydantic import BaseModel, ConfigDict, Field


class PlanoPublico(BaseModel):
    """Plano de assinatura exibido na vitrine (público — sem stripe_price_id)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    intervalo: str  # mensal | anual
    preco: float


class CheckoutAvulsoRequest(BaseModel):
    """Inicia o checkout de um curso avulso (one-time, cartão + Pix)."""

    curso_slug: str = Field(..., min_length=1, max_length=120)


class CheckoutAssinaturaRequest(BaseModel):
    """Inicia o checkout de uma assinatura (recorrente). `plano_id` = PlanoAssinatura."""

    plano_id: uuid.UUID


class CheckoutCriado(BaseModel):
    """Sessão de Checkout criada — o frontend redireciona para `checkout_url`."""

    checkout_url: str
    session_id: str


class WebhookRecebido(BaseModel):
    """Resposta padrão dos webhooks de pagamento."""

    received: bool = True

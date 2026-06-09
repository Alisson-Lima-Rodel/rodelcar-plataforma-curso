from pydantic import BaseModel, Field


class CheckoutAvulsoRequest(BaseModel):
    """Inicia o checkout de um curso avulso (one-time, cartão + Pix)."""

    curso_slug: str = Field(..., min_length=1, max_length=120)


class CheckoutCriado(BaseModel):
    """Sessão de Checkout criada — o frontend redireciona para `checkout_url`."""

    checkout_url: str
    session_id: str


class WebhookRecebido(BaseModel):
    """Resposta padrão dos webhooks de pagamento."""

    received: bool = True

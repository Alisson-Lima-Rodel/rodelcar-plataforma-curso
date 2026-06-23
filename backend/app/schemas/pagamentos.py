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


class StatusCompra(BaseModel):
    """Status REAL de uma sessão de checkout, para a tela /sucesso não afirmar
    'pago' sem confirmação. O acesso é concedido SÓ pelo webhook; aqui apenas
    REPORTAMOS o `payment_status` do Stripe e se a matrícula já foi criada.

    estado: 'liberado'  → matrícula ativa já existe (pode entrar no curso);
            'processando'→ pago no Stripe, mas o webhook ainda não liberou;
            'pendente'   → pagamento não confirmado (ex.: Pix aguardando).
    """

    estado: str
    payment_status: str
    acesso_liberado: bool
    curso_slug: str | None = None


class WebhookRecebido(BaseModel):
    """Resposta padrão dos webhooks de pagamento."""

    received: bool = True

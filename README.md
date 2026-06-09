# RödelCar — Repositório inicial

Kit de início (Fase 2 do playbook). Sobe o ambiente local e já deixa o Claude Code
configurado com CLAUDE.md, MCP de Postgres, subagent revisor e hooks de proteção.

## Pré-requisitos
Docker + Docker Compose, Node 20+, Python 3.12, Claude Code e `jq` (usado pelos hooks).

## Passo a passo

```bash
# 1. Inicializar o git
git init

# 2. Criar o frontend Next.js (TypeScript + Tailwind + App Router)
npx create-next-app@latest frontend --ts --tailwind --app --eslint --use-npm --yes
#   (se aparecer prompt de Turbopack/alias, aceite os padrões)

cd frontend
npx shadcn@latest init        # siga os prompts (base color, etc.)
npm install @tanstack/react-query @tremor/react recharts
cd ..

# 3. Variáveis de ambiente do backend
cp backend/.env.example backend/.env
# gere a chave Fernet e cole em RODELCAR_FERNET_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 4. Subir tudo
docker compose up --build
#   backend  -> http://localhost:8000/health
#   frontend -> http://localhost:3000
#   db       -> localhost:5432  (user/pass/db: rodelcar)

# 5. Verificar o MCP de Postgres no Claude Code
#   Abra o Claude Code na raiz do projeto e rode:  /mcp
#   Depois peça, por exemplo:  "liste as tabelas do banco"
#   (o servidor @modelcontextprotocol/server-postgres é somente leitura — seguro p/ dev)
```

## O que já vem configurado para o Claude Code
- `CLAUDE.md` — regras sempre ativas (stack, convenções, segurança/LGPD, hospedagem).
- `.mcp.json` — MCP de Postgres (introspecção de schema e SELECTs).
- `.claude/agents/code-reviewer.md` — subagent revisor (somente leitura).
  Invoque com: "use o subagent code-reviewer para revisar minhas mudanças".
- `.claude/settings.json` + `.claude/hooks/` — bloqueia edição de `.env`/segredos
  (PreToolUse) e formata o código após cada edição (PostToolUse).

## Pagamentos — Stripe (avulso + assinaturas)

Checkout HOSPEDADO da Stripe (cartão + Pix), com liberação de acesso **somente via webhook**.

1. **Variáveis** (no `.env`, à mão): `STRIPE_SECRET_KEY` (sk_test_...),
   `STRIPE_WEBHOOK_SECRET` (whsec_..., vem do `stripe listen` ou do Dashboard),
   `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`.
2. **Criar Products/Prices em BRL** (uma vez) e gravar o `price_id` em cada curso:
   ```bash
   docker compose run --rm --entrypoint python backend -m scripts.stripe_setup
   ```
   (ou crie no Dashboard e cole o `price_id` em `cursos.stripe_price_id`).
3. **Migrar o schema** (colunas `stripe_customer_id`/`stripe_price_id` + tabela `webhook_eventos`):
   ```bash
   docker compose run --rm --entrypoint alembic backend upgrade head
   ```
4. **Webhook em dev** — encaminhe os eventos da Stripe para o backend local:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/webhooks/pagamento/stripe
   ```
   O `stripe listen` imprime o `whsec_...` → coloque em `STRIPE_WEBHOOK_SECRET`.
5. **Testar** — autenticado, `POST /api/v1/checkout/avulso {"curso_slug": "..."}`,
   abra o `checkout_url` e pague com o cartão de teste **`4242 4242 4242 4242`**
   (qualquer data futura/CVC). Pix em teste confirma em ~3 min via
   `checkout.session.async_payment_succeeded`. A `Matricula` é criada/renovada pelo webhook.

> **Pix é assíncrono:** o `checkout.session.completed` pode chegar ainda não pago; a
> confirmação vem em `checkout.session.async_payment_succeeded`. Acesso liberado só no webhook.

### Assinaturas (acesso total ao catálogo)

O `scripts.stripe_setup` também cria os planos **Mensal** e **Anual** (`planos_assinatura`).
Endpoints (autenticados), corpo `{"plano_id": "<uuid>"}`:
- `POST /api/v1/checkout/assinatura-cartao` — `mode=subscription`, cartão.
- `POST /api/v1/checkout/assinatura-pix` — Pix Automático (`mandate_options`: teto `amount_type=maximum`
  = 2× o valor do plano, `payment_schedule=monthly`). Cobra no ciclo+3 dias (notificação pré-débito),
  fica em `processing` nesse período; IOF incide por cobrança.

Webhook trata: `invoice.paid` (libera/renova acesso a **todos os cursos** até o fim do ciclo —
`current_period_end`), `invoice.payment_failed` (registra recusa) e `customer.subscription.deleted`
(expira as matrículas da assinatura). Acesso sempre liberado **só pelo webhook**.

## Hospedagem (produção)
- **Front-end** → Vercel (deploy direto do diretório `frontend/`).
- **Banco** → Supabase. Use a connection string com `postgresql+asyncpg://...` no
  `DATABASE_URL` do backend (e a string `postgresql://...` no MCP, se for apontar p/ prod).
- **Back-end** → Render / Railway / Fly.io (processo persistente, porque o job de
  vigência roda continuamente). Configure as variáveis de ambiente lá (sem `.env`).

## Próximos passos
Siga o `prompts-e-execucao.md` a partir da Fase 3 (backend núcleo). O modelo de dados
já está em `backend/app/models/__init__.py` e o contrato em `docs/api-contract.md`.

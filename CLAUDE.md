# RödelCar — Regras do projeto (sempre ativas)

Ecossistema digital da RödelCar Câmbios: portal público de captação/venda + LMS para mecânicos.

## Stack
- Back-end: Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, JWT, Fernet.
- Front-end: Next.js 14 (App Router), TypeScript, Tailwind, Shadcn/UI, Tremor, Recharts, TanStack Query.
- Banco: PostgreSQL 16. Infra: Docker / Docker Compose.

## Convenções de trabalho
- Uma fase por vez. Rode e teste antes de commitar. Commits pequenos e descritivos.
- NUNCA commitar `.env`. Segredos só em variáveis de ambiente.
- Antes de implementar um endpoint, confira o contrato em @docs/api-contract.md.

## Back-end
- SQLAlchemy 2.0 async (asyncpg). Modelos em @backend/app/models/__init__.py — não duplicar.
- Pydantic v2 para schemas de entrada/saída. Erros no formato padrão do contrato.
- DATABASE_URL do backend usa `postgresql+asyncpg://`. O MCP de Postgres usa `postgresql://`.

## Front-end
- App Router com route groups: `(public)` em SSG/SSR (SEO) e `(lms)` dinâmico/logado.
- Shadcn/UI + Tailwind para componentes padrão; CSS puro nos momentos de assinatura
  (hero, player, textura de blueprint, animações). Tokens em @docs/design-system.md.
- Dark mode pleno no LMS. Dados via TanStack Query (mocks em frontend/mocks na fase inicial).

## Segurança e LGPD
- CPF cifrado em repouso (Fernet); nunca em log nem em URL.
- Webhooks de pagamento: validar assinatura + idempotência por gateway_transaction_id.
- Vigência da assinatura checada NO LOGIN e por JOB agendado (APScheduler).

## Hospedagem
- Front: Vercel. Banco: Supabase. Back-end: host com processo persistente
  (Render/Railway/Fly), porque o job de vigência precisa rodar continuamente.

## Comandos
- Subir local: `docker compose up --build` (backend :8000, frontend :3000, db :5432).
- Testes backend: `pytest` dentro de backend/.

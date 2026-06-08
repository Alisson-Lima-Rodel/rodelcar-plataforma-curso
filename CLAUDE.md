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
- Rate limiting é PADRÃO de toda a API: limite default por IP aplicado a todas as
  rotas pela `SlowAPIMiddleware` (config em @backend/app/core/ratelimit.py). Endpoint
  novo já nasce protegido — não decorar um a um. Teto via env `RATE_LIMIT_PUBLIC`.
  Para um limite diferente numa rota, use `@limiter.limit("...")` (exige `request: Request`);
  para isentar (ex.: webhooks server-to-server), `@limiter.exempt`. O 429 sai no envelope
  de erro padrão (`code: RATE_LIMITED`) via handler SÍNCRONO em app.main.
- CORS dirigido por env `CORS_ORIGINS` (lista por vírgula); em produção, domínio da Vercel.
- Login/refresh têm teto estrito anti brute-force (`RATE_LIMIT_AUTH`, default `5/minute`)
  via `@limiter.limit(auth_limit)` — separado do teto público.
- Em produção (`ENVIRONMENT=production`), `Settings` faz **fail-fast**: recusa subir com
  `JWT_SECRET` fraco/curto (<32), `RODELCAR_FERNET_KEY` ausente, `INTERNAL_TOKEN`
  placeholder ou `DATABASE_URL` com credenciais default. Segurança não é opcional no deploy.
- Security headers (nosniff, X-Frame-Options DENY, CSP, Referrer-Policy) em toda resposta;
  HSTS só sob produção (assume TLS no proxy).

## Hospedagem
- Front: Vercel. Banco: Supabase. Back-end: host com processo persistente
  (Render/Railway/Fly), porque o job de vigência precisa rodar continuamente.
- Produção roda via `entrypoint.sh` SEM `--reload`: múltiplos workers (`WEB_CONCURRENCY`)
  e `--proxy-headers`/`--forwarded-allow-ips` para o rate limit usar o IP real do
  `X-Forwarded-For` (atrás de LB/proxy, sem isso o limite vira global).
- Rate limit em multi-instância exige storage compartilhado: defina
  `RATELIMIT_STORAGE_URI=redis://...` (sem ele, cada processo conta sozinho).

## Comandos
- Subir local: `docker compose up --build` (backend :8000, frontend :3000). O banco
  é o Supabase (sem serviço `db` local): defina `DATABASE_URL` no `.env`. Ver @docs/supabase.md.
- Testes backend: `pytest` dentro de backend/.

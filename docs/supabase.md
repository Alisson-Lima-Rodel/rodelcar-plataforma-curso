# Banco — Supabase (Postgres gerenciado)

O banco saiu da imagem Docker local e passou a ser o **Supabase**. A aplicação
conecta com um **papel dedicado (`rodelcar_app`), não o superusuário `postgres`**.

## Conexão

A conexão **direta** (`db.<ref>.supabase.co:5432`) resolve **só em IPv6** — não
funciona em redes/Docker sem IPv6. Por isso a aplicação conecta pelo **pooler (IPv4)
do Supabase em modo sessão (porta 5432)**:

- Host: `aws-1-sa-east-1.pooler.supabase.com` · porta `5432` · banco `postgres`.
- Usuário: `rodelcar_app.yftihybhqvvewwdbblhf` (no pooler o login é `<papel>.<project_ref>`).
- Driver: `postgresql+asyncpg://`. SSL é forçado automaticamente (o host contém
  `supabase.co`) — ver `Settings.db_connect_args` em `backend/app/core/config.py`;
  override por `DATABASE_SSL`.

> A connection string com `[YOUR-PASSWORD]` do painel usa o usuário **`postgres` (root)**
> e o host **direto (IPv6)** — **não** usar na aplicação. Use `rodelcar_app` via pooler.

## Setup (uma vez)

1. **Criar o papel da aplicação** — Supabase → SQL Editor (logado como `postgres`),
   rode [`backend/scripts/supabase_role.sql`](../backend/scripts/supabase_role.sql),
   trocando `__APP_PASSWORD__` pela senha que está em `DATABASE_URL` no `.env`.

2. **Definir `DATABASE_URL` no `.env`** (à mão — `.env` é protegido), via pooler:
   ```dotenv
   DATABASE_URL=postgresql+asyncpg://rodelcar_app.yftihybhqvvewwdbblhf:SENHA@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
   ```

3. **Migrar o schema** (cria as tabelas; **não** insere dados):
   ```bash
   # Via Docker (DATABASE_URL já cabeada pelo compose a partir do .env):
   docker compose run --rm --entrypoint alembic backend upgrade head
   ```
   Local (fora do Docker), exporte a URL antes — o pydantic lê o .env do diretório
   atual, então rode da raiz com a env no ambiente:
   ```bash
   # PowerShell:  $env:DATABASE_URL="postgresql+asyncpg://rodelcar_app:...@db.<ref>.supabase.co:5432/postgres"
   cd backend && alembic upgrade head
   ```
   Não rode `scripts/seed.py` — o banco fica só com o schema real, sem dados de
   exemplo/mock.

## Notas de deploy

- A conexão **direta** (`db.<ref>.supabase.co:5432`) é **IPv6-only**; em hosts sem IPv6
  (Docker local, muitos provedores) use o **pooler em modo sessão (5432)** — adequado ao
  backend persistente + job de vigência (APScheduler). O **modo transação (6543)** é só
  para serverless e exige desativar prepared statements no asyncpg
  (`prepared_statement_cache_size=0`). Confirme host/porta/usuário no painel:
  Project Settings → Database → Connection string → **Session pooler**.
- Em produção (`ENVIRONMENT=production`) o `Settings` faz fail-fast e **recusa subir**
  se a `DATABASE_URL` usar o superusuário `postgres`.
- **Rotação de senha**: `alter role rodelcar_app with password '...';` e atualize o `.env`.

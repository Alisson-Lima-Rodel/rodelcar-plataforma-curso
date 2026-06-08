-- ============================================================================
-- RödelCar — papel de aplicação no Supabase (NÃO usar o superusuário `postgres`)
-- ============================================================================
-- A aplicação NÃO deve conectar como `postgres` (root). Este script cria um
-- papel dedicado, sem superusuário, com permissão apenas para gerenciar o
-- schema `public` (criar/migrar/ler/escrever as tabelas da plataforma).
--
-- COMO RODAR (uma única vez):
--   1. Supabase → SQL Editor (logado, usa o `postgres`).
--   2. Troque __APP_PASSWORD__ pela senha que está em DATABASE_URL no .env.
--   3. Execute.
--
-- Depois, rode as migrações conectado como rodelcar_app:
--   cd backend && alembic upgrade head
-- ----------------------------------------------------------------------------

create role rodelcar_app with login password '__APP_PASSWORD__'
  nosuperuser nocreatedb nocreaterole noreplication;

-- Conectar ao banco e gerenciar o schema public (criar tabelas nas migrações)
grant connect on database postgres to rodelcar_app;
grant usage, create on schema public to rodelcar_app;

-- Objetos já existentes e futuros no schema public
grant all on all tables    in schema public to rodelcar_app;
grant all on all sequences in schema public to rodelcar_app;
alter default privileges in schema public grant all on tables    to rodelcar_app;
alter default privileges in schema public grant all on sequences to rodelcar_app;

-- Para ROTACIONAR a senha depois:
--   alter role rodelcar_app with password 'nova-senha';
-- Para REMOVER o papel (cuidado, precisa reatribuir/zerar objetos):
--   drop owned by rodelcar_app; drop role rodelcar_app;

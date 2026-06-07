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

## Hospedagem (produção)
- **Front-end** → Vercel (deploy direto do diretório `frontend/`).
- **Banco** → Supabase. Use a connection string com `postgresql+asyncpg://...` no
  `DATABASE_URL` do backend (e a string `postgresql://...` no MCP, se for apontar p/ prod).
- **Back-end** → Render / Railway / Fly.io (processo persistente, porque o job de
  vigência roda continuamente). Configure as variáveis de ambiente lá (sem `.env`).

## Próximos passos
Siga o `prompts-e-execucao.md` a partir da Fase 3 (backend núcleo). O modelo de dados
já está em `backend/app/models/__init__.py` e o contrato em `docs/api-contract.md`.

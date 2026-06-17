#!/usr/bin/env bash
# Sobe a aplicação LOCAL (sem Docker): backend (FastAPI :8000) em background e
# frontend (Next :3000) em primeiro plano. Ctrl+C encerra os dois.
# Uso:  bash scripts/dev-local.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[ -f .env ] || { echo ".env não encontrado no root (veja .env.example)"; exit 1; }

# Python 3.12 (launcher do Windows ou python3.12).
PY="py -3.12"; command -v py >/dev/null 2>&1 || PY="python3.12"

# Backend: venv + deps (1ª vez).
if [ ! -x backend/.venv/Scripts/python.exe ] && [ ! -x backend/.venv/bin/python ]; then
  echo "Criando venv (Python 3.12) + instalando deps do backend…"
  $PY -m venv backend/.venv
fi
# Caminho ABSOLUTO do python do venv (Windows usa Scripts/, Unix usa bin/).
VENVPY="$ROOT/backend/.venv/Scripts/python.exe"; [ -x "$VENVPY" ] || VENVPY="$ROOT/backend/.venv/bin/python"
"$VENVPY" -m pip install --upgrade pip >/dev/null
"$VENVPY" -m pip install -r backend/requirements.txt >/dev/null

# Frontend: deps + .env.local (NEXT_PUBLIC_* vindas do .env do root).
[ -d frontend/node_modules ] || (cd frontend && npm install)
grep -E '^[[:space:]]*NEXT_PUBLIC_' .env | grep -v '^[[:space:]]*#' > frontend/.env.local || true

# Backend em background; frontend em foreground. Mata o backend ao sair.
( cd backend && "$VENVPY" -m uvicorn app.main:app --reload --port 8000 --env-file ../.env ) &
BACK_PID=$!
trap 'kill "$BACK_PID" 2>/dev/null || true' EXIT

echo "Backend  → http://localhost:8000 (docs: /docs)"
echo "Frontend → http://localhost:3000"
cd frontend && npm run dev

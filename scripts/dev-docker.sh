#!/usr/bin/env bash
# Sobe a aplicação via Docker Compose: backend (:8000) + frontend (:3000).
# Uso:  bash scripts/dev-docker.sh
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

[ -f .env ] || { echo ".env não encontrado no root (veja .env.example)"; exit 1; }

echo "Subindo backend (:8000) e frontend (:3000) via Docker — Ctrl+C para parar."
docker compose up --build

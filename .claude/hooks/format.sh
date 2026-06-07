#!/usr/bin/env bash
set -euo pipefail
# Formata o arquivo apos a edicao (nao bloqueia se falhar).
path=$(jq -r '.tool_input.path // .tool_input.file_path // ""')
case "$path" in
  *.py) command -v ruff >/dev/null 2>&1 && ruff format "$path" >/dev/null 2>&1 || true ;;
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css)
    command -v npx >/dev/null 2>&1 && npx --yes prettier --write "$path" >/dev/null 2>&1 || true ;;
esac
exit 0

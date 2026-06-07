#!/usr/bin/env bash
set -euo pipefail
# Recebe o JSON do evento no stdin. Bloqueia edicao de arquivos sensiveis.
# Requer jq instalado. exit 2 = bloqueia a acao.
path=$(jq -r '.tool_input.path // .tool_input.file_path // ""')
case "$path" in
  *.env|*/.env|*.env.*|*/.git/*|*secret*|*credential*)
    echo "Politica: edicao de '$path' bloqueada. Altere esse arquivo manualmente." 1>&2
    exit 2
    ;;
esac
exit 0

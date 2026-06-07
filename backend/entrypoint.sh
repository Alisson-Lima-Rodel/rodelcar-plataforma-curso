#!/bin/sh
set -e

IS_PROD=false
case "$(echo "${ENVIRONMENT:-development}" | tr '[:upper:]' '[:lower:]')" in
  production|prod) IS_PROD=true ;;
esac

if [ -z "$RODELCAR_FERNET_KEY" ]; then
  if [ "$IS_PROD" = "true" ]; then
    echo "ERRO: RODELCAR_FERNET_KEY obrigatoria em producao (CPF cifrado exige chave fixa)." >&2
    exit 1
  fi
  # Dev: chave efemera so para subir local — CPF cifrado nao sobrevive a restart.
  export RODELCAR_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  echo "AVISO: RODELCAR_FERNET_KEY nao definida — usando chave efemera de dev (NAO usar em producao)"
fi

if [ "$IS_PROD" = "true" ]; then
  # Producao: sem --reload; multiplos workers; honra X-Forwarded-* do proxy/LB
  # (essencial p/ rate limit por IP real e logs corretos atras do load balancer).
  exec uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
    --no-server-header
else
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

# Sobe a aplicacao via Docker Compose: backend (:8000) + frontend (:3000).
# O banco e o Supabase (DATABASE_URL no .env do root). As envs do Panda tambem
# saem do .env (PANDA_API_KEY, NEXT_PUBLIC_PANDA_EMBED_BASE, ...).
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\dev-docker.ps1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

if (-not (Test-Path -LiteralPath ".env")) {
  Write-Error ".env nao encontrado no root. Crie a partir do .env.example (DATABASE_URL, JWT_SECRET, ...)."
  exit 1
}

Write-Host "Subindo backend (:8000) e frontend (:3000) via Docker. Ctrl+C para parar." -ForegroundColor Cyan
docker compose up --build

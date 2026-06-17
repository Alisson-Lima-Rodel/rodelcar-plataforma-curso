# Sobe a aplicacao LOCAL (sem Docker): backend (FastAPI :8000) + frontend (Next :3000),
# cada um em sua janela. O banco e o Supabase (via DATABASE_URL do .env do root).
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\dev-local.ps1
#
# 1a execucao: cria o venv (Python 3.12) + instala deps do back, e npm install no front.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$EnvFile = Join-Path $Root ".env"

if (-not (Test-Path -LiteralPath $EnvFile)) {
  Write-Error "$EnvFile nao encontrado. Crie o .env a partir do .env.example (DATABASE_URL, JWT_SECRET, ...)."
  exit 1
}

# Backend: venv Python 3.12 + dependencias.
$VenvPy = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPy)) {
  Write-Host "Criando venv (Python 3.12) e instalando dependencias do backend..." -ForegroundColor Cyan
  py -3.12 -m venv (Join-Path $BackendDir ".venv")
  & $VenvPy -m pip install --upgrade pip
  & $VenvPy -m pip install -r (Join-Path $BackendDir "requirements.txt")
}

# Frontend: dependencias + .env.local (NEXT_PUBLIC_* vindas do .env do root).
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
  Write-Host "Instalando dependencias do frontend (npm install)..." -ForegroundColor Cyan
  Push-Location $FrontendDir
  npm install
  Pop-Location
}
# O Next le o .env do proprio diretorio; geramos um .env.local so com as NEXT_PUBLIC_*
# (gitignored por frontend/.env*.local).
$nextVars = Get-Content -LiteralPath $EnvFile |
  Where-Object { $_ -match '^\s*NEXT_PUBLIC_' -and $_ -notmatch '^\s*#' }
Set-Content -LiteralPath (Join-Path $FrontendDir ".env.local") -Value $nextVars -Encoding utf8

# Sobe os dois em janelas separadas.
$backendCmd = "Set-Location -LiteralPath '$BackendDir'; " +
  "& '$VenvPy' -m uvicorn app.main:app --reload --port 8000 --env-file '$EnvFile'"
$frontendCmd = "Set-Location -LiteralPath '$FrontendDir'; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "Backend  -> http://localhost:8000  (docs: /docs)" -ForegroundColor Green
Write-Host "Frontend -> http://localhost:3000" -ForegroundColor Green
Write-Host "Abri duas janelas. Feche cada uma (Ctrl+C) para parar o servico." -ForegroundColor DarkGray

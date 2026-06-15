from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.ratelimit import limiter
from app.core.scheduler import iniciar_scheduler, parar_scheduler
from app.routers import admin, auth, aulas, avaliacoes, certificados, checkout, conteudo, cursos, depoimentos, internal, leads, me, progresso, quizzes, webhooks_pagamento, webhooks_wa


@asynccontextmanager
async def lifespan(app: FastAPI):
    iniciar_scheduler()
    yield
    parar_scheduler()


app = FastAPI(
    title="RödelCar API",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Rate limiter por IP (slowapi): o limite default da app é aplicado a TODAS as
# rotas pela SlowAPIMiddleware — é o padrão da API. Overrides pontuais por rota
# usam @limiter.limit(...) no handler.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security headers (defesa em profundidade) ─────────────────────────────────
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # API JSON não serve HTML/scripts; CSP restritiva evita uso indevido.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for k, v in _SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    # HSTS só faz sentido sob HTTPS (produção atrás de TLS).
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


# ── Formato de erro padronizado do contrato ───────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "ERROR", "message": str(detail), "details": None}},
    )


# Síncrono de propósito: a SlowAPIMiddleware (sync_check_limits) ignora handlers
# assíncronos e cai no default texto-puro — um def garante nosso envelope padrão.
@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": {
            "code": "RATE_LIMITED",
            "message": "Muitas requisições. Tente novamente em instantes.",
            "details": None,
        }},
        headers={"Retry-After": "60"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Remove a chave `input` de cada erro: não ecoa o valor enviado pelo usuário
    # (evita devolver senha/e-mail digitados no corpo da resposta de erro).
    detalhes = [
        {k: v for k, v in err.items() if k != "input"} for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": {
            "code": "VALIDATION_ERROR",
            "message": "Dados de entrada inválidos.",
            "details": jsonable_encoder(detalhes),
        }},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cursos.router, prefix="/api/v1")
app.include_router(avaliacoes.router, prefix="/api/v1")
app.include_router(depoimentos.router, prefix="/api/v1")
app.include_router(conteudo.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(aulas.router, prefix="/api/v1")
app.include_router(progresso.router, prefix="/api/v1")
app.include_router(quizzes.router, prefix="/api/v1")
app.include_router(certificados.router, prefix="/api/v1")
app.include_router(internal.router, prefix="/api/v1")
app.include_router(webhooks_wa.router, prefix="/api/v1")
app.include_router(checkout.router, prefix="/api/v1")
app.include_router(webhooks_pagamento.router, prefix="/api/v1")


# ── Infra ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["infra"])
async def health():
    return {"status": "ok", "service": "rodelcar-backend"}

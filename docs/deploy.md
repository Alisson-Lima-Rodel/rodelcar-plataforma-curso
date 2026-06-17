# Go-live — Runbook de produção (RödelCar)

Arquitetura de produção:

| Camada    | Onde            | Observação |
|-----------|-----------------|------------|
| Frontend  | **Vercel**      | Next.js 14, SSG/SSR. Domínio: `rodelcar.com.br`. |
| Backend   | **Railway**     | FastAPI em Docker, processo persistente (job de vigência). 1 réplica no lançamento. |
| Banco     | **Supabase**    | Postgres 16, papel `rodelcar_app`, SSL. Ver [supabase.md](supabase.md). |
| Pagamento | **Stripe**      | Checkout hospedado + webhook. Trocar de **test** para **live**. |

> Esta é a sequência de lançamento. Faça **backend → CORS → frontend → Stripe live → smoke tests**.
> Segredos só entram nos painéis (Railway/Vercel) como variáveis de ambiente — **nunca** no git.

---

## Checkpoint — o que bloqueia o lançamento vs o que pode esperar

**Bloqueadores reais** (sem isso a app não funciona ou cobra errado):
- Backend de pé (envs ⚠️ + fail-fast verde) com `DATABASE_URL` correto.
- Frontend com `NEXT_PUBLIC_API_URL` → backend, e `CORS_ORIGINS` casando com a origem do front.
- Stripe **live** (chave + webhook + `price_id`/cupom recriados) — só na hora de cobrar de verdade.

**Opcionais — degradam gracioso, ligam depois sem tocar em código:**
- **E-mail (SMTP):** sem ele a app roda normal; só não envia boas-vindas/confirmação/certificado
  (envio é best-effort pós-commit, não trava o pagamento). Preencha `SMTP_*` quando tiver as credenciais.
- **WhatsApp, Google Places, YouTube, Supabase Storage (upload de capa), `NEXT_PUBLIC_*` de SEO,
  `NEXT_PUBLIC_PANDA_EMBED_BASE` (vídeo):** cada bloco some/dorme se a env faltar (vídeo vira placeholder).

**Pausa segura recomendada:** suba **backend + frontend com Stripe em modo TESTE**, valide o fluxo
inteiro com cartões de teste (sem gastar) e só então faça o **passo 4 (Stripe live)**. E-mail e os
demais opcionais entram a qualquer momento depois.

---

## 0. Pré-requisitos

- Conta na Railway, Vercel, Supabase e Stripe.
- Domínio `rodelcar.com.br` com acesso ao DNS.
- Projeto Supabase de produção pronto (papel `rodelcar_app`, ver [supabase.md](supabase.md)).

Gere os 3 segredos do backend (rode local, guarde num gerenciador de senhas):

```bash
# JWT_SECRET (>= 32 chars)
python -c "import secrets; print(secrets.token_urlsafe(48))"
# INTERNAL_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(48))"
# RODELCAR_FERNET_KEY (chave de cifra do CPF — NUNCA perca: CPFs ficam ilegíveis)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 1. Banco (Supabase)

Se o projeto Supabase de produção for **novo**, aplique as migrações apontando o
Alembic para a `DATABASE_URL` de produção (papel `rodelcar_app`):

```bash
# de dentro de backend/, com DATABASE_URL=postgresql+asyncpg://rodelcar_app:...@<pooler>/postgres
alembic upgrade head        # head atual: a0b1c2d3e4f5 (quizzes)
```

Crie o primeiro admin (Administrador) direto no banco ou por script — o cadastro
de admin não é público. Depois disso, gerencie a equipe pelo painel `/admin`.

> Se a produção reaproveitar o Supabase já em uso, as migrações já estão no head — pule.

---

## 2. Backend na Railway

1. **New Project → Deploy from GitHub** → selecione o repositório.
2. No serviço, **Settings → Root Directory = `backend`** (monorepo). O Railway lê o
   `backend/Dockerfile` e o `backend/railway.toml` (healthcheck `/health`, 1 réplica).
   > ⚠️ **Sem isso o build falha** com `Railpack could not determine how to build the app`
   > (ele tentou a raiz, que não tem Dockerfile). Se o log mostrar `using ... railpack` e
   > listar `frontend/ backend/ docs/`, o Root Directory não foi aplicado. Com `backend`
   > configurado, o log mostra `using Dockerfile`. Se ainda assim usar Railpack, em
   > **Settings → Build** force **Builder = Dockerfile**.
3. **Variables** — defina (⚠️ = obrigatória; o backend recusa subir sem/ com valor fraco):

   **Núcleo / segurança**
   | Variável | Valor |
   |----------|-------|
   | `ENVIRONMENT` ⚠️ | `production` |
   | `DATABASE_URL` ⚠️ | `postgresql+asyncpg://rodelcar_app:<senha>@<pooler-host>:6543/postgres` |
   | `JWT_SECRET` ⚠️ | (gerado no passo 0) |
   | `RODELCAR_FERNET_KEY` ⚠️ | (gerado no passo 0) |
   | `INTERNAL_TOKEN` ⚠️ | (gerado no passo 0) |
   | `CORS_ORIGINS` ⚠️ | `https://rodelcar.com.br,https://www.rodelcar.com.br` (sem `*`) |
   | `FORWARDED_ALLOW_IPS` ⚠️ | `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10,fd00::/8` |
   | `WEB_CONCURRENCY` | `1` (1 réplica/1 worker → scheduler roda uma vez; sem Redis) |
   | `RATE_LIMIT_PUBLIC` | `120/minute` |
   | `RATE_LIMIT_AUTH` | `5/minute` |

   **Pagamento (Stripe — começar em test, virar live no passo 4)**
   | Variável | Valor |
   |----------|-------|
   | `STRIPE_SECRET_KEY` | `sk_live_...` |
   | `STRIPE_WEBHOOK_SECRET` | `whsec_...` (do endpoint live — passo 4) |
   | `STRIPE_SUCCESS_URL` | `https://rodelcar.com.br/sucesso` |
   | `STRIPE_CANCEL_URL` | `https://rodelcar.com.br/` |

   **E-mail transacional (boas-vindas/confirmação/certificado)**
   | Variável | Valor |
   |----------|-------|
   | `SMTP_HOST` / `SMTP_PORT` | ex.: `smtp.resend.com` / `465` |
   | `SMTP_USER` / `SMTP_PASSWORD` | credenciais do provedor |
   | `EMAIL_FROM` | `noreply@rodelcar.com.br` (domínio verificado no provedor) |

   **Opcionais** (cada bloco degrada gracioso se ausente)
   | Variável | Para quê |
   |----------|----------|
   | `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` / `SUPABASE_BUCKET` | upload de capa de curso (Storage) |
   | `GOOGLE_PLACES_API_KEY` / `GOOGLE_PLACE_ID` | nota/reviews do Google na prova social |
   | `YOUTUBE_API_KEY` | metadados ao cadastrar vídeo |
   | `WA_PROVIDER` + chaves (`WA_META_*` / `WA_TWILIO_*` / `WA_ZAPI_*`) | WhatsApp (vigência + certificado) |
   | `PANDA_API_KEY` | upload de vídeo pela tela admin + duração/capa + retenção (ver [video-panda.md](video-panda.md)) |
   | `PANDA_DRM_ENABLED` / `PANDA_DRM_GROUP_ID` / `PANDA_DRM_SECRET` | embed privado (token assinado). Fail-fast se ligado sem grupo/segredo |
   | `CERT_MIN_WATCH_RATIO` | fração assistida exigida no certificado (default 0.85) |
   | `PORTAL_URL` / `RENOVACAO_URL` | já têm default `https://rodelcar.com.br` |

4. **Deploy.** Gere um domínio público (**Settings → Networking → Generate Domain**) —
   ex.: `rodelcar-backend.up.railway.app`. Anote: é a base da API.
5. **Healthcheck:** `GET https://<backend>/health` deve responder `{"status":"ok"}`.

> Se o deploy **falhar no boot** com "Configuração insegura para ENVIRONMENT=production",
> o fail-fast pegou um segredo fraco/ausente — a mensagem lista exatamente o quê. Corrija e re-deploy.

### Por que 1 réplica / `WEB_CONCURRENCY=1`?
O job de vigência (APScheduler) sobe junto com o processo. Com 2+ workers/réplicas ele
rodaria em duplicado (a idempotência protege a correção, mas duplica chamadas pagas, ex.:
Google Places). Para escalar depois: defina `RATELIMIT_STORAGE_URI=redis://...` **e** adicione
uma trava no scheduler (advisory lock do Postgres) antes de subir o nº de workers.

---

## 3. Frontend na Vercel

1. **Import Project** → repositório → **Root Directory = `frontend`**. Framework: Next.js (auto).
2. **Environment Variables:**
   | Variável | Valor |
   |----------|-------|
   | `NEXT_PUBLIC_API_URL` | `https://<backend>.up.railway.app/api/v1` |
   | `NEXT_PUBLIC_SITE_URL` | `https://rodelcar.com.br` (canônico p/ SEO/sitemap/OG) |
   | `NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION` | token do Google Search Console (sem `<meta>`) |
   | `NEXT_PUBLIC_PANDA_EMBED_BASE` | `https://player-vz-XXXX.tv.pandavideo.com.br/embed/` |
3. **Domínio:** adicione `rodelcar.com.br` (+ `www`) e aponte o DNS conforme a Vercel.
4. Deploy.

> Depois que o backend conhecer o domínio final, garanta que `CORS_ORIGINS` (passo 2)
> lista exatamente as origens da Vercel/domínio — senão o front toma erro de CORS.

---

## 4. Stripe — virar para LIVE ⚠️ (gotcha de go-live)

Test e live são mundos separados na Stripe: **os `price_id`/`coupon_id` de teste NÃO existem em live.**

1. Ative a conta (live mode) e pegue a `sk_live_...`.
2. **Recrie em live mode** os produtos/preços e cupons e **atualize os IDs no banco**:
   - `cursos.stripe_price_id` (compra avulsa de cada curso) → `price_live_...`
   - `planos_assinatura.stripe_price_id` (assinaturas) → `price_live_...`
   - cupons (`cupons.stripe_coupon_id` / `stripe_promotion_code_id`) recriados em live, ou
     recrie pelo painel `/admin/cupons` com a chave live ativa.
3. **Webhook:** Dashboard → Developers → Webhooks → **Add endpoint**:
   - URL: `https://<backend>.up.railway.app/api/v1/webhooks/pagamento/stripe`
   - Eventos: `checkout.session.completed`, `invoice.paid`,
     `customer.subscription.deleted` (e os demais que o handler trata).
   - Copie o **Signing secret** (`whsec_...`) → `STRIPE_WEBHOOK_SECRET` na Railway → re-deploy.
4. `STRIPE_SECRET_KEY` = `sk_live_...` na Railway.

> O acesso ao conteúdo é liberado **somente** pelo webhook (assinado + idempotente). Sem o
> `STRIPE_WEBHOOK_SECRET` correto, o fail-fast bloqueia o boot (não deixa o webhook fail-open).

---

## 5. Smoke tests pós-deploy

- [ ] `GET /health` → `{"status":"ok"}`.
- [ ] Cadastro + login de aluno no front (token, dashboard carrega).
- [ ] Página de curso renderiza; **Rich Results Test** mostra `aggregateRating` (se houver review).
- [ ] Compra real de teste (cartão live de baixo valor ou um cupom 100%): Checkout →
      webhook → matrícula concede acesso → e-mail de confirmação chega.
- [ ] Concluir aulas + passar no quiz → emitir certificado → página `/verificar/<codigo>` abre.
- [ ] Reembolso dentro de 7 dias (painel do aluno) reverte acesso.
- [ ] Admin `/admin` loga e gere conteúdo/cupom.

---

## 6. Pós-go-live

- **Search Console:** verificar o domínio (token do passo 3), enviar `https://rodelcar.com.br/sitemap.xml`.
- **Backups:** confirmar backups automáticos do Supabase; **guardar `RODELCAR_FERNET_KEY`** num cofre
  (perdê-la = CPFs ilegíveis; rotação documentada em `models/__init__.py::_get_fernet`).
- **Monitorar:** logs da Railway (erros 5xx), entregabilidade de e-mail, e a fila de
  notificações de vigência (job diário 06:00 UTC).
- **Escalar** (quando o tráfego pedir): Redis no rate limit + trava no scheduler antes de `WEB_CONCURRENCY>1`.

---

## Referência rápida — URLs

- Health: `GET /health`
- Webhook Stripe: `POST /api/v1/webhooks/pagamento/stripe`
- API base (front): `NEXT_PUBLIC_API_URL = https://<backend>/api/v1`

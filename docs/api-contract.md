# RödelCar — Contrato da API

Base URL (dev): `http://localhost:8000/api/v1`
Formato: JSON. Datas em ISO 8601 (UTC). IDs em UUID v4.

---

## Convenções gerais

**Autenticação:** Bearer JWT no header `Authorization: Bearer <access_token>`.
Rotas marcadas com 🔒 exigem aluno autenticado.

**Paginação (listagens):** query params `?page=1&size=20`. Resposta:
```json
{ "items": [ ... ], "total": 124, "page": 1, "size": 20 }
```

**Formato de erro (padrão único em toda a API):**
```json
{
  "error": {
    "code": "MATRICULA_EXPIRADA",
    "message": "Sua assinatura expirou em 2026-01-10.",
    "details": null
  }
}
```
Códigos HTTP: 200/201 sucesso, 400 validação, 401 não autenticado,
403 sem permissão/matrícula, 404 não encontrado, 409 conflito (ex: e-mail já existe),
422 erro de schema, 429 rate limit, 500 erro interno.

**Rate limiting:** limite por IP aplicado a **todas** as rotas. Ao exceder, retorna
`429` com `error.code = "RATE_LIMITED"` e header `Retry-After` (segundos). O cliente
deve respeitar o `Retry-After` antes de tentar de novo.

---

## 1. Auth

### `POST /auth/login`
```json
// request
{ "email": "joao@email.com", "senha": "..." }
// response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### `POST /auth/refresh`
```json
// request
{ "refresh_token": "eyJ..." }
// response 200 -> mesmo formato do login
```
- **Rotação:** cada refresh invalida o token usado e emite um novo par. O refresh
  expira em **7 dias** (`JWT_REFRESH_EXPIRE_DAYS`).
- **Detecção de reuso:** reapresentar um refresh já rotacionado/revogado retorna
  `401 REFRESH_REUTILIZADO` e **revoga todas as sessões** do aluno (sinal de roubo).
- Token inválido/expirado/desconhecido → `401 REFRESH_INVALIDO`.

### `POST /auth/logout`
```json
// request
{ "refresh_token": "eyJ..." }
// response 204 (idempotente) — revoga o refresh informado
```

### `GET /auth/me` 🔒
```json
// response 200
{
  "id": "uuid",
  "nome": "João Silva",
  "email": "joao@email.com",
  "matriculas_ativas": 2
}
```

---

## 2. Cursos (público)

### `GET /cursos`
Lista a vitrine. Query opcional: `?tipo=premium|avulso`.
```json
// response 200
{
  "items": [
    {
      "id": "uuid",
      "slug": "i-motion",
      "titulo": "Diagnóstico I-Motion",
      "descricao_curta": "Domine o câmbio automatizado I-Motion.",
      "tipo": "avulso",
      "preco": 497.00,
      "validade_dias": 365,
      "thumbnail_url": "https://...",
      "total_modulos": 6,
      "total_aulas": 42,
      "destaque": false
    }
  ],
  "total": 8, "page": 1, "size": 20
}
```

### `GET /cursos/{slug}`
Detalhe completo (página de venda).
```json
// response 200
{
  "id": "uuid",
  "slug": "i-motion",
  "titulo": "Diagnóstico I-Motion",
  "descricao": "Texto longo...",
  "tipo": "avulso",
  "preco": 497.00,
  "validade_dias": 365,
  "thumbnail_url": "https://...",
  "modulos": [
    { "id": "uuid", "titulo": "Fundamentos", "ordem": 1, "total_aulas": 7 }
  ]
}
```

---

## 3. Matrículas e acesso 🔒

### `GET /me/matriculas`
```json
// response 200
{
  "items": [
    {
      "id": "uuid",
      "curso": { "id": "uuid", "slug": "i-motion", "titulo": "Diagnóstico I-Motion" },
      "status": "ativo",                       // ativo | expirado | bloqueado
      "data_inicio": "2025-06-01T00:00:00Z",
      "data_expiracao": "2026-06-01T00:00:00Z",
      "dias_restantes": 360,
      "progresso_percentual": 34.5
    }
  ]
}
```

### `GET /me/dashboard` 🔒
Dados consolidados do painel do aluno.
```json
// response 200
{
  "ultima_aula": {
    "aula_id": "uuid", "titulo": "Leitura de scanner",
    "curso_slug": "i-motion", "percentual": 60
  },
  "alertas": [
    { "tipo": "vigencia", "nivel": "warning", "mensagem": "Plano expira em 12 dias." }
  ],
  "resumo": { "cursos_ativos": 2, "aulas_concluidas": 18, "certificados": 1 }
}
```

---

## 4. Aulas, player e progresso 🔒

### `GET /aulas/{id}` 🔒
Exige matrícula ativa no curso da aula; caso contrário 403 `MATRICULA_EXPIRADA`.
```json
// response 200
{
  "id": "uuid",
  "titulo": "Leitura de scanner",
  "modulo_id": "uuid",
  "panda_video_id": "abc123",        // id do embed; o token de player é gerado server-side
  "duracao_segundos": 1280,
  "materiais": [
    { "id": "uuid", "nome": "Esquema elétrico I-Motion", "url_pdf": "https://..." }
  ],
  "progresso": { "concluida": false, "percentual": 60 }
}
```

### `POST /progresso` 🔒
```json
// request
{ "aula_id": "uuid", "percentual": 75, "concluida": false }
// response 200
{ "aula_id": "uuid", "percentual": 75, "concluida": false, "curso_percentual": 38.2 }
```

---

## 5. Certificados 🔒 / verificação pública

### `POST /certificados/{matricula_id}` 🔒
Emite certificado se o curso estiver 100% concluído (senão 409).
```json
// response 201
{ "id": "uuid", "codigo_verificacao": "RC-2026-AB12CD", "emitido_em": "2026-06-06T..." }
```

### `GET /certificados/{codigo}/verificar`  (público)
```json
// response 200
{ "valido": true, "aluno_nome": "João Silva", "curso": "Diagnóstico I-Motion", "emitido_em": "..." }
```

---

## 6. Leads — agendamento de avaliação (público)

### `POST /leads`
```json
// request
{
  "nome": "Maria",
  "telefone": "+55 51 99999-0000",
  "email": "maria@email.com",
  "tipo_servico": "avaliacao_cambio",
  "mensagem": "Câmbio automático trepidando.",
  "origem": "hero_cta"            // alimenta o analytics
}
// response 201
{ "id": "uuid", "status": "novo" }
```

---

## 7. Webhook de pagamento (servidor a servidor)

### `POST /webhooks/pagamento/{gateway}`
`{gateway}` = `mercadopago` | `stripe` | `asaas`.

Regras obrigatórias:
- Validar **assinatura** do header conforme o gateway (rejeitar 401 se inválida).
- **Idempotência:** `gateway_transaction_id` único; reprocessar o mesmo evento não
  cria matrícula duplicada (responder 200 sem efeito).
- Em pagamento confirmado → cria/renova `Matricula` (status `ativo`,
  `data_expiracao = agora + curso.validade_dias`).

> **Nota de implementação (Stripe):** o payload abaixo é *ilustrativo/normalizado*. O
> handler real consome o **evento nativo do Stripe** (`checkout.session.completed`,
> `checkout.session.async_payment_succeeded` p/ Pix) e resolve o aluno por
> `metadata.app_user_id` e o curso por `metadata.curso_slug` (mais robusto que `aluno_email`).
> Validação **fail-closed**: sem `STRIPE_WEBHOOK_SECRET` retorna 503.

```json
// exemplo de payload normalizado internamente (varia por gateway)
{
  "gateway_transaction_id": "mp_1234567",
  "status": "approved",
  "valor": 497.00,
  "aluno_email": "joao@email.com",
  "curso_slug": "i-motion"
}
// response 200
{ "received": true }
```

### `GET /planos` (público)
Planos de assinatura **ativos** para a vitrine (card Premium). Não expõe
`stripe_price_id`; o checkout em si é autenticado.

```json
// response 200
[ { "id": "uuid", "nome": "Assinatura Anual", "intervalo": "anual", "preco": 499.00 } ]
```

### Checkout (autenticado 🔒)
- `POST /checkout/avulso` `{ "curso_slug": "..." }` → `{ "checkout_url", "session_id" }`
  (Stripe Checkout hospedado; cartão+Pix com fallback card-only).
- `POST /checkout/assinatura-cartao` `{ "plano_id": "uuid" }` → idem (recorrente).
- `POST /checkout/assinatura-pix` `{ "plano_id": "uuid" }` → idem (Pix Automático,
  exige Pix habilitado na conta Stripe; senão 400 `PIX_INDISPONIVEL`).

O front redireciona o navegador para `checkout_url`; o acesso é liberado SOMENTE
pelo webhook (a `success_url` é apenas UX).

---

## 8. Eventos analíticos

### `POST /eventos`
Recebe os disparos dos atributos `data-event` do frontend.
```json
// request
{
  "nome_evento": "cta_agendar_click",
  "sessao_id": "sess_abc",
  "propriedades": { "secao": "hero", "dispositivo": "mobile" }
}
// response 202  (aceito; processamento assíncrono)
{ "accepted": true }
```

---

## 9. Job de notificações (interno)

> Acionado pelo scheduler (APScheduler) ou por um cron externo. **Não usa JWT de aluno** —
> autentica por segredo de serviço no header `X-Internal-Token` (401 se inválido).

### `POST /internal/notificacoes/processar`
Executa o ciclo de vigência: varre as matrículas, enfileira notificações nos marcos
configurados e envia as pendentes (e-mail/WhatsApp), gravando cada uma em `Notificacao`.
```json
// request (corpo opcional)
{ "marcos": ["15d", "7d", "1d", "expirado"], "dry_run": false }
// response 200
{ "verificadas": 320, "enfileiradas": 14, "enviadas": 13, "falhas": 1 }
```
Idempotente por `(matricula_id, tipo, canal, marco)`: rodar de novo no mesmo dia não reenvia
a mesma mensagem. Com `dry_run: true`, apenas conta o que seria enviado, sem disparar.

---

## 10. Webhook de status do WhatsApp (servidor a servidor)

> Recebe os callbacks de entrega do provedor (Meta Cloud API / Twilio / Z-API) e atualiza
> o status da notificação. Validar a assinatura/token do provedor (401 se inválido).

### `GET /webhooks/whatsapp/status` — verificação (handshake inicial)
Alguns provedores (ex.: Meta Cloud API) exigem um handshake na configuração. Ecoar o desafio
apenas se o `hub.verify_token` conferir:
```
GET /webhooks/whatsapp/status?hub.mode=subscribe&hub.verify_token=<TOKEN>&hub.challenge=<X>
// response 200 (texto puro): <X>
```

### `POST /webhooks/whatsapp/status`
```json
// payload normalizado internamente (o formato bruto varia por provedor)
{
  "provedor_msg_id": "wamid.abc123",
  "status": "delivered",           // sent | delivered | read | failed
  "erro": null
}
// efeito: localiza a Notificacao por provedor_msg_id e atualiza o status (enviada | falhou)
// response 200
{ "received": true }
```

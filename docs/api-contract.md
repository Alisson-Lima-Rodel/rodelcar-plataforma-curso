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

## 7. Estoque de carros (público)

### `GET /estoque`
```json
// response 200
{
  "items": [
    { "id": "uuid", "modelo": "Jetta TSI", "ano": 2021, "preco": 98000.00,
      "status": "disponivel", "thumbnail_url": "https://..." }
  ],
  "total": 12, "page": 1, "size": 20
}
```

---

## 8. Webhook de pagamento (servidor a servidor)

### `POST /webhooks/pagamento/{gateway}`
`{gateway}` = `mercadopago` | `stripe` | `asaas`.

Regras obrigatórias:
- Validar **assinatura** do header conforme o gateway (rejeitar 401 se inválida).
- **Idempotência:** `gateway_transaction_id` único; reprocessar o mesmo evento não
  cria matrícula duplicada (responder 200 sem efeito).
- Em pagamento confirmado → cria/renova `Matricula` (status `ativo`,
  `data_expiracao = agora + curso.validade_dias`).

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

---

## 9. Eventos analíticos

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

## 10. Job de notificações (interno)

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

## 11. Webhook de status do WhatsApp (servidor a servidor)

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

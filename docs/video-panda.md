# Vídeo — Panda Video (LMS)

Integração de vídeo do LMS. **Panda = aulas pagas** (player privado, progresso,
DRM); **YouTube = prova social** do portal (depoimentos/vídeos, em `/videos`). Não
misturar: aula nunca vai pro YouTube; prova social nunca usa Panda.

## Arquitetura

- **Player do LMS:** SmartPlayer SDK do Panda (`frontend/src/components/lms/smart-player.tsx`),
  carregado via `https://player.pandavideo.com.br/api.v2.js` (fila `pandascripttag`).
  Controles nativos: velocidade, qualidade adaptativa, **legendas**, PiP, fullscreen,
  **capítulos**. Eventos `panda_timeupdate/pause/ended` alimentam o progresso.
- **Segurança:** a `PANDA_API_KEY` fica **só no backend**. O upload é **mediado**: o
  backend cria a sessão (chave no `Upload-Metadata`, server-to-server) e devolve só a
  URL; o browser sobe o arquivo direto pra ela, sem nunca ver a chave.
- Cliente Panda no backend: `backend/app/core/panda.py`.

## Variáveis de ambiente

Backend (repassadas no `docker-compose.yml`; em produção, no Railway):

| Var | Para quê |
|-----|----------|
| `PANDA_API_KEY` | Header `Authorization` (SEM "Bearer"). Liga upload/duração/retenção. |
| `PANDA_UPLOADER_BASE` | Base do uploader TUS (região). Default `https://uploader-us01.pandavideo.com.br`. |
| `PANDA_FOLDER_ID` | Pasta opcional onde os uploads caem na biblioteca. |
| `PANDA_DRM_ENABLED` | `true` liga o embed privado (token assinado). |
| `PANDA_DRM_GROUP_ID` / `PANDA_DRM_SECRET` | Watermark group do Panda (id + segredo). |
| `PANDA_DRM_TOKEN_TTL` | TTL (s) do token DRM por sessão. Default 14400 (4h). |
| `CERT_MIN_WATCH_RATIO` | Fração da aula que precisa ter sido assistida p/ o certificado. Default 0.85. |

Frontend (Vercel): `NEXT_PUBLIC_PANDA_EMBED_BASE` — base do embed
(ex.: `https://player-vz-XXXX.tv.pandavideo.com.br/embed/`). Sem ela, o player cai no
placeholder. Produção faz **fail-fast** se `PANDA_DRM_ENABLED=true` sem grupo/segredo.

## Upload de vídeo pela tela admin

No admin → conteúdo do curso → editar aula → **Enviar vídeo**:

1. `POST /admin/aulas/{id}/upload-url` `{filename,size,content_type?}` → o backend cria a
   sessão TUS no Panda, gera o `video_id` (UUID v4), grava em `aula.panda_video_id` e
   devolve `{video_id, upload_url}`.
2. O browser faz `PATCH` do arquivo na `upload_url` (TUS, sem a chave) — com barra de progresso.
3. `POST /admin/aulas/{id}/sync-panda` → *Get video properties* preenche `duracao_segundos`
   (e devolve `status`/`thumbnail`). A duração só fica pronta após a conversão — clique
   **Sincronizar duração** depois se o vídeo ainda estava convertendo.

Respostas de erro: 503 sem `PANDA_API_KEY`; 502 em falha do Panda; 409 sem vídeo.

## Legendas (IA) e idiomas

A legenda automática é **gerada no dashboard do Panda** (ou via API `create-ai-subtitles`);
a renderização e o seletor de idioma são **nativos do player** (`controls` inclui `captions`).
O selo **"Legendado em PT/EN/ES"** na página de venda vem de `Curso.idiomas_legenda`
(editável no admin do curso, separado por vírgula).

## Capítulos

Configurados **no dashboard do Panda**, por vídeo. O SmartPlayer os exibe nativamente na
barra de progresso/menu (nosso `controls` inclui `progress` e `settings`). Nada a codar.

## DRM (token assinado / embed privado)

1. No Panda (Security), crie um **watermark group** e ative **Domain Protection**.
2. Defina `PANDA_DRM_ENABLED=true`, `PANDA_DRM_GROUP_ID`, `PANDA_DRM_SECRET`.
3. O backend assina um JWT curto por sessão (`drm_group_id` + `exp`, HS256 com o segredo) e
   o devolve em `GET /aulas/{id}` (`player_token`/`drm_group_id`) e no preview. O player
   anexa `?watermark=<jwt>&drm_group_id=<id>` ao embed. DRM desligado → `player_token=null`
   → embed público.

## Analytics de retenção

`GET /admin/aulas/{id}/retencao` → curva de retenção (Panda Analytics), normalizada em
`[{segundo, percentual}]`. No admin, botão **Retenção** por aula abre um modal (CSS puro:
barras + retenção média + maior queda).

## Anti-fraude do certificado

`progresso.segundos_assistidos` é acumulado **pelo servidor** (delta de relógio entre pings,
limitado a 30s) — o cliente nunca envia esse total. O gate do certificado exige
`segundos_assistidos ≥ CERT_MIN_WATCH_RATIO × duracao_segundos` por aula, além de
`concluida`. Logo, `percentual=100` instantâneo (scrub/POST direto) não emite certificado.

## Resume (retomada cross-device)

`progresso.posicao_segundos` guarda o último segundo assistido; ao reabrir, o player dá
`seek` (via `startTime`). Independe do `saveProgress` local do Panda (que é por dispositivo).

## Migrações Alembic

- `b1c2d3e4f5a6` — `progresso.posicao_segundos` + `progresso.segundos_assistidos`.
- `c2d3e4f5a6b7` — `cursos.idiomas_legenda`.

## CSP (`frontend/next.config.mjs`)

- `script-src` libera `https://player.pandavideo.com.br` (SDK `api.v2.js`).
- `connect-src` libera `https://*.pandavideo.com.br` (XHR/postMessage do player + uploader TUS).
- `frame-src` / `media-src` já liberavam `https://*.tv.pandavideo.com.br` (embed/streams).

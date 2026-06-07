# RödelCar — Design System

> Documento para guiar o **Claude Design** e, depois, a implementação em
> Next.js + Tailwind + Shadcn/UI. Direção, tokens e regras de uso.

## Direção conceitual: "Engenharia de Precisão"
Oficina premium de elite. A interface deve transmitir **competência técnica e
confiança** sem parecer fria. Pense em painel de diagnóstico de carro de alto padrão
cruzado com plataforma de educação moderna. Dark mode é o estado natural.

- **Para o dono do carro** (portal): reduzir ansiedade, transmitir autoridade
  (Taylor Rödel), levar à ação — agendar avaliação. CTAs quentes e diretos.
- **Para o mecânico** (LMS): foco, clareza e sensação de progresso. Estética que
  respeita quem é técnico — precisa, organizada, sem ruído.

Diferencial memorável: o **acento vermelho incandescente** (cor de metal aquecido /
luz de diagnóstico) sobre superfícies grafite quase pretas, com finos traços de
"blueprint" como textura de fundo.

---

## Cores (tokens)

Fundo e superfícies — grafite frio, com leve viés azulado (sensação técnica):
```
--bg            #0A0C10   /* fundo base, quase preto */
--surface       #13161C   /* cards, painéis */
--surface-2     #1B1F27   /* elementos elevados, inputs */
--border        #262B34
--border-strong #333A45
```
Texto:
```
--text          #F2F4F7
--text-muted    #98A0AD
--text-subtle   #6B7280
```
Marca / conversão — vermelho incandescente (energia, calor, ação):
```
--primary        #E5372B
--primary-hover  #C72A20
--primary-fg     #FFFFFF   /* texto branco sobre o botão vermelho */
--primary-soft   rgba(229,55,43,0.13)   /* fundos, badges, glow */
```
Diagnóstico / dados — ciano frio, usado com parcimônia (links, gráficos, info):
```
--accent        #22D3EE
```
Semânticos:
```
--success #22C55E   --warning #F59E0B   --danger #EF4444   --info #38BDF8
```
Paleta de dados (Tremor/Recharts, nesta ordem):
`#E5372B, #22D3EE, #A78BFA, #34D399, #F472B6, #FBBF24`

Regra de ouro: **vermelho é raro e poderoso** — reserve-o para a ação principal de cada
tela (1 CTA dominante). Tudo o mais vive em grafite + texto. Cor distribuída por igual
mata a hierarquia.

---

## Tipografia
Fontes distintas e disponíveis no Google Fonts:

- **Display / títulos:** `Archivo` (grotesca industrial, forte, comercial). Pesos 700/800.
  Para o Hero, considerar `Archivo Expanded` em 800.
- **Corpo / UI:** `Hanken Grotesk` (limpa, precisa, calorosa). Pesos 400/500/600.
- **Mono / técnico:** `JetBrains Mono` — códigos de certificado, specs, números,
  tags de evento, rótulos "técnicos". Dá credibilidade de engenharia.

Escala (rem): display 3.5 · h1 2.5 · h2 1.875 · h3 1.375 · base 1 · sm 0.875 · xs 0.75.
Títulos com `letter-spacing` levemente negativo (-0.02em) e line-height apertado (1.05–1.15).
Corpo com line-height 1.6.

---

## Forma, espaço e profundidade
- **Espaçamento:** escala base 4px → 4,8,12,16,24,32,48,64,96.
- **Raios:** cards 14px · botões/inputs 10px · badges/pills 9999px.
- **Profundidade no escuro:** diferenciar por **luminosidade da superfície + borda 1px**,
  não por sombra preta pesada. No CTA vermelho e em hovers, usar **glow** suave
  (`box-shadow: 0 0 0 1px var(--primary), 0 8px 30px -8px rgba(229,55,43,.5)`).
- **Textura de fundo:** grade fina de blueprint (linhas a ~6% de opacidade) e/ou
  gradiente radial vermelho muito sutil atrás do Hero. Nada que compita com o conteúdo.

---

## Componentes (mapeados para Shadcn/UI)
- **Button** — `primary` (vermelho, texto branco, glow no hover) é a ação única dominante;
  `secondary` (surface-2 + border); `ghost`; `link` (ciano). Cantos 10px, peso 600.
- **Card** — surface + borda 1px + raio 14px; no hover a borda clareia para
  `--border-strong` e sobe 1px. Base de cards de curso e widgets do dashboard.
- **Card de curso (e-commerce)** — thumbnail, **Badge** de tipo (Premium = vermelho/dourado,
  Avulso = neutro), preço em Archivo, selo "1 ano de acesso" em mono, CTA.
- **Badge** — Premium com leve gradiente vermelho; status com cores semânticas + ícone
  (nunca só cor).
- **Tabs / Accordion** — navegação entre módulos no player (Accordion lateral).
- **Progress** — trilha grafite, preenchimento vermelho; usar em curso e gamificação.
- **Dialog / Sheet** — formulário de agendamento e login.
- **Input/Form** — fundo surface-2, borda 1px, **focus ring vermelho** (2px).
- **Alert** — banner de vigência da assinatura (warning) no topo do dashboard.
- **Avatar, Tooltip, Skeleton** (loading), **Sonner** (toasts).
- **Tremor** — KPI cards e gráficos do dashboard de evolução / futuro BI.

---

## Motion
Sutil e proposital. Transições 150–250ms ease-out. Um **page-load orquestrado** com
revelação escalonada (stagger) no Hero vale mais que micro-animações espalhadas.
Hover dos cards com leve elevação + clareamento de borda. Barras de progresso animam
o preenchimento ao montar. Respeitar `prefers-reduced-motion`.

---

## Voz e tom
- **Portal:** confiante, direto, especialista. Frases curtas. Foco em resultado e
  segurança ("Avaliação precisa do seu câmbio automático"). CTA no imperativo.
- **LMS:** encorajador e objetivo, linguagem de quem domina o ofício. Celebrar
  progresso e conclusão sem infantilizar.

## Acessibilidade
Contraste mínimo AA (texto sobre grafite e sobre vermelho já atende). Foco sempre visível
(ring vermelho). Status nunca só por cor — sempre com ícone/rótulo. Áreas de toque ≥ 44px.

---

## Diretrizes por tela (para o Claude Design produzir)
1. **Hero / agendamento** — título forte (Archivo), subtítulo de credibilidade,
   1 CTA vermelho "Agendar avaliação", fundo blueprint + glow. Prova de autoridade próxima.
2. **Prova social** — grade de vídeos do YouTube (thumbnails 16:9) + carrossel de
   depoimentos com estrelas vermelho.
3. **Vitrine e-commerce** — destaque do Pacote Premium Anual (card maior, badge dourado)
   + grade de módulos avulsos com selo de validade.
4. **Dashboard do aluno** — saudação, alerta de vigência (se houver), card "retomar
   última aula", KPIs (Tremor), trilhas com Progress.
5. **Player de aula** — vídeo dominante, Accordion de módulos à lateral, aba de
   materiais (PDFs) e aba de dúvidas/comunidade.
6. **Gamificação / certificado** — barras de progresso, marcos, certificado com código
   em mono e selo de verificação.

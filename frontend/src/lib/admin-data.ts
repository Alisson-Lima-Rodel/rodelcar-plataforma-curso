/* Admin — esquemas de entidade (colunas da tabela + campos do formulário).
   Os dados vêm do backend via TanStack Query (ver lib/admin-api.ts +
   components/admin/remote-entity-manager.tsx). Aqui só a forma de cada cadastro. */

export type AdminItem = Record<string, string | number | boolean | null>;

export type BadgeVariant =
  | "premium"
  | "amber"
  | "cyan"
  | "success"
  | "warning"
  | "";

export type FieldType =
  | "text"
  | "number"
  | "date"
  | "select"
  | "textarea"
  | "toggle"
  | "stars"
  | "password";

export interface Column {
  key: string;
  label: string;
  kind?: string;
}

export interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  col?: "full";
  options?: string[];
  on?: string | boolean;
  off?: string | boolean;
  hint?: string;
}

export interface EntitySchema {
  label: string;
  singular: string;
  icon: string;
  title: (it: AdminItem) => string;
  search: (it: AdminItem) => string;
  filter: { key: string; options: string[] };
  columns: Column[];
  fields: FieldDef[];
  defaults: AdminItem;
}

export type EntityKey =
  | "students"
  | "courses"
  | "testimonials"
  | "packages"
  | "plans"
  | "videos"
  | "faq"
  | "admins";

export const ADMIN_USER = {
  name: "Rödel",
  role: "Administrador",
  initials: "RC",
};

let _id = 100;
export const uid = () => "id" + ++_id;

export const ENTITIES: Record<EntityKey, EntitySchema> = {
  students: {
    label: "Alunos",
    singular: "aluno",
    icon: "users",
    title: (it) => String(it.nome),
    search: (it) => `${it.nome} ${it.email} ${it.telefone ?? ""}`,
    filter: { key: "status", options: ["Todos", "Ativo", "Inativo"] },
    // Cursos/Vigência/Status vêm derivados da matrícula (somente-leitura).
    columns: [
      { key: "nome", label: "Aluno", kind: "user" },
      { key: "telefone", label: "Telefone", kind: "muted" },
      { key: "matriculas", label: "Cursos", kind: "center" },
      { key: "vigencia", label: "Vigência", kind: "date" },
      { key: "status", label: "Status", kind: "badgeStatus" },
    ],
    fields: [
      { key: "nome", label: "Nome completo", type: "text", col: "full" },
      { key: "email", label: "E-mail", type: "text" },
      { key: "telefone", label: "Telefone", type: "text" },
      {
        key: "senha",
        label: "Senha",
        type: "password",
        col: "full",
        hint: "Mín. 6 caracteres. Em edição, deixe em branco para manter a atual.",
      },
    ],
    defaults: {
      nome: "",
      email: "",
      telefone: "",
      senha: "",
    },
  },
  courses: {
    label: "Cursos",
    singular: "curso",
    icon: "book",
    title: (it) => String(it.titulo),
    search: (it) => `${it.titulo} ${it.badge_label}`,
    filter: {
      key: "badge_label",
      options: ["Todos", "Automatizado", "Automático", "Dupla embreagem"],
    },
    columns: [
      { key: "titulo", label: "Curso", kind: "strong" },
      { key: "badge_label", label: "Sistema", kind: "badgeSystem" },
      { key: "nivel", label: "Nível" },
      { key: "aulas_total", label: "Aulas", kind: "center" },
      { key: "preco", label: "Preço", kind: "price" },
    ],
    fields: [
      { key: "slug", label: "Slug (URL)", type: "text" },
      { key: "titulo", label: "Título do curso", type: "text", col: "full" },
      { key: "tagline", label: "Chamada (tagline)", type: "text", col: "full" },
      {
        key: "badge_label",
        label: "Sistema",
        type: "select",
        options: ["Automatizado", "Automático", "Dupla embreagem"],
      },
      {
        key: "nivel",
        label: "Nível",
        type: "select",
        options: ["Iniciante", "Intermediário", "Avançado"],
      },
      {
        key: "preco",
        label: "Preço (R$)",
        type: "number",
        hint: "Sincroniza com a Stripe: muda o valor cobrado nas próximas vendas.",
      },
      { key: "preco_antigo", label: "Preço antigo (R$)", type: "number" },
      { key: "horas", label: "Carga horária", type: "text" },
      { key: "aulas_total", label: "Nº de aulas", type: "number" },
      { key: "rating", label: "Nota (0–5)", type: "number" },
      { key: "alunos", label: "Nº de alunos", type: "number" },
      { key: "ordem", label: "Ordem na vitrine", type: "number" },
    ],
    defaults: {
      slug: "",
      titulo: "",
      tagline: "",
      badge_label: "Automatizado",
      nivel: "Intermediário",
      preco: 397,
      preco_antigo: 597,
      horas: "6h00",
      aulas_total: 30,
      rating: 4.8,
      alunos: 0,
      ordem: 0,
    },
  },
  testimonials: {
    label: "Depoimentos",
    singular: "depoimento",
    icon: "message",
    title: (it) => String(it.nome),
    search: (it) => `${it.nome} ${it.papel} ${it.texto}`,
    filter: { key: "status", options: ["Todos", "Aprovado", "Pendente"] },
    columns: [
      { key: "nome", label: "Autor", kind: "user" },
      { key: "papel", label: "Papel" },
      { key: "estrelas", label: "Nota", kind: "stars" },
      { key: "texto", label: "Depoimento", kind: "truncate" },
      { key: "status", label: "Status", kind: "badgeStatus" },
    ],
    fields: [
      { key: "nome", label: "Nome", type: "text" },
      { key: "papel", label: "Papel · Cidade", type: "text" },
      { key: "estrelas", label: "Avaliação", type: "stars", col: "full" },
      { key: "texto", label: "Depoimento", type: "textarea", col: "full" },
      {
        key: "status",
        label: "Aprovado para o site",
        type: "toggle",
        on: "Aprovado",
        off: "Pendente",
      },
    ],
    defaults: {
      nome: "",
      papel: "",
      estrelas: 5,
      texto: "",
      status: "Pendente",
    },
  },
  packages: {
    label: "Pacotes",
    singular: "pacote",
    icon: "award",
    title: (it) => String(it.nome),
    search: (it) => String(it.nome),
    filter: { key: "status", options: ["Todos", "Ativo", "Inativo"] },
    columns: [
      { key: "nome", label: "Pacote", kind: "strong" },
      { key: "cursos", label: "Cursos", kind: "center" },
      { key: "parcelas", label: "Parcelamento" },
      { key: "preco", label: "Preço", kind: "price" },
      { key: "status", label: "Status", kind: "badgeStatus" },
    ],
    fields: [
      { key: "nome", label: "Nome do pacote", type: "text", col: "full" },
      { key: "preco", label: "Preço (R$)", type: "number" },
      { key: "preco_antigo", label: "Preço antigo (R$)", type: "number" },
      { key: "parcelas", label: "Parcelamento", type: "text" },
      { key: "cursos", label: "Qtd. de cursos", type: "number" },
      {
        key: "inclui",
        label: "Inclui (um item por linha)",
        type: "textarea",
        col: "full",
      },
      {
        key: "status",
        label: "Pacote ativo",
        type: "toggle",
        on: "Ativo",
        off: "Inativo",
      },
    ],
    defaults: {
      nome: "",
      preco: 997,
      preco_antigo: 1297,
      parcelas: "12x de R$ 99,70",
      cursos: 3,
      inclui: "",
      status: "Ativo",
    },
  },
  // Planos de assinatura (Premium): dão acesso ao catálogo INTEIRO. É o que o
  // card "Assinar Premium" da vitrine vende — diferente de Pacotes (marketing).
  plans: {
    label: "Planos (assinatura)",
    singular: "plano",
    icon: "infinity",
    title: (it) => String(it.nome),
    search: (it) => `${it.nome} ${it.intervalo}`,
    filter: { key: "status", options: ["Todos", "Ativo", "Inativo"] },
    columns: [
      { key: "nome", label: "Plano", kind: "strong" },
      { key: "intervalo", label: "Intervalo", kind: "muted" },
      { key: "preco", label: "Preço", kind: "price" },
      { key: "status", label: "Status", kind: "badgeStatus" },
    ],
    fields: [
      { key: "nome", label: "Nome do plano", type: "text", col: "full" },
      {
        key: "intervalo",
        label: "Intervalo",
        type: "select",
        options: ["mensal", "anual"],
      },
      {
        key: "preco",
        label: "Preço (R$)",
        type: "number",
        hint: "Sincroniza com a Stripe: salvar gera um novo Price para as PRÓXIMAS vendas (assinaturas existentes mantêm o valor contratado).",
      },
      {
        key: "stripe_price_id",
        label: "Stripe Price ID",
        type: "text",
        col: "full",
        hint: "Deixe VAZIO para criar automaticamente na Stripe ao salvar. Preencha só para usar um Price já existente.",
      },
      {
        key: "status",
        label: "Plano ativo (aparece na vitrine)",
        type: "toggle",
        on: "Ativo",
        off: "Inativo",
      },
    ],
    defaults: {
      nome: "",
      intervalo: "anual",
      preco: 499,
      stripe_price_id: "",
      status: "Ativo",
    },
  },
  videos: {
    label: "Vídeos",
    singular: "vídeo",
    icon: "play",
    title: (it) => String(it.titulo),
    search: (it) => `${it.titulo} ${it.views ?? ""}`,
    filter: { key: "status", options: ["Todos", "Ativo", "Inativo"] },
    columns: [
      { key: "titulo", label: "Vídeo", kind: "strong" },
      { key: "duracao", label: "Duração", kind: "muted" },
      { key: "views", label: "Views", kind: "muted" },
      { key: "status", label: "Status", kind: "badgeStatus" },
    ],
    fields: [
      { key: "titulo", label: "Título do vídeo", type: "text", col: "full" },
      {
        key: "youtube_url",
        label: "Link do YouTube",
        type: "text",
        col: "full",
        hint: "Cole a URL do vídeo. Em branco, o card leva ao canal.",
      },
      { key: "duracao", label: "Duração (ex.: 12:48)", type: "text" },
      { key: "views", label: "Views (ex.: 84 mil)", type: "text" },
      { key: "ordem", label: "Ordem na vitrine", type: "number" },
      {
        key: "status",
        label: "Exibir no site",
        type: "toggle",
        on: "Ativo",
        off: "Inativo",
      },
    ],
    defaults: {
      titulo: "",
      youtube_url: "",
      duracao: "",
      views: "",
      ordem: 0,
      status: "Ativo",
    },
  },
  faq: {
    label: "FAQ",
    singular: "pergunta",
    icon: "book",
    title: (it) => String(it.pergunta),
    search: (it) => `${it.pergunta} ${it.resposta}`,
    filter: { key: "status", options: ["Todos", "Ativo", "Inativo"] },
    columns: [
      { key: "pergunta", label: "Pergunta", kind: "strong" },
      { key: "resposta", label: "Resposta", kind: "truncate" },
      { key: "status", label: "Status", kind: "badgeStatus" },
    ],
    fields: [
      { key: "pergunta", label: "Pergunta", type: "text", col: "full" },
      { key: "resposta", label: "Resposta", type: "textarea", col: "full" },
      { key: "ordem", label: "Ordem", type: "number" },
      {
        key: "status",
        label: "Exibir no site",
        type: "toggle",
        on: "Ativo",
        off: "Inativo",
      },
    ],
    defaults: {
      pergunta: "",
      resposta: "",
      ordem: 0,
      status: "Ativo",
    },
  },
  admins: {
    label: "Administradores",
    singular: "administrador",
    icon: "shield",
    title: (it) => String(it.nome),
    search: (it) => `${it.nome} ${it.email} ${it.papel}`,
    filter: {
      key: "papel",
      options: ["Todos", "Administrador", "Editor", "Suporte"],
    },
    columns: [
      { key: "nome", label: "Usuário", kind: "user" },
      { key: "papel", label: "Papel", kind: "badgeRole" },
      { key: "ultimo_acesso", label: "Último acesso", kind: "muted" },
      { key: "ativo", label: "Status", kind: "badgeAtivo" },
    ],
    fields: [
      { key: "nome", label: "Nome", type: "text" },
      { key: "email", label: "E-mail de acesso", type: "text" },
      {
        key: "papel",
        label: "Papel",
        type: "select",
        options: ["Administrador", "Editor", "Suporte"],
        hint: "Administrador: acesso total · Editor: cursos, pacotes e depoimentos · Suporte: alunos.",
      },
      {
        key: "senha",
        label: "Senha",
        type: "password",
        hint: "Mín. 8 caracteres. Em edição, deixe em branco para manter a atual.",
      },
      {
        key: "ativo",
        label: "Usuário ativo",
        type: "toggle",
        on: true,
        off: false,
      },
    ],
    defaults: {
      nome: "",
      email: "",
      papel: "Suporte",
      senha: "",
      ativo: true,
    },
  },
};

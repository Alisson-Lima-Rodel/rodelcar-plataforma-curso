/* Admin — seed data + esquemas de entidade (colunas + campos do formulário).
   CRUD em memória nesta fase; trocar por chamadas ao backend (TanStack Query +
   mutations) quando os endpoints de gestão existirem. */

export type AdminItem = Record<string, string | number>;

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
  on?: string;
  off?: string;
  hint?: string;
}

export interface EntitySchema {
  label: string;
  singular: string;
  icon: string;
  seed: AdminItem[];
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
  | "admins";

export const ADMIN_USER = {
  name: "Rödel",
  role: "Administrador",
  initials: "RC",
};

let _id = 100;
export const uid = () => "id" + ++_id;

const SEED_STUDENTS: AdminItem[] = [
  {
    id: "s1",
    nome: "Rogério Alves",
    email: "rogerio.alves@oficina.com",
    cidade: "Gravataí/RS",
    plano: "Premium Anual",
    matriculas: 4,
    vigencia: "2026-07-23",
    status: "Ativo",
  },
  {
    id: "s2",
    nome: "Daniela Prado",
    email: "daniela@prado.com.br",
    cidade: "Curitiba/PR",
    plano: "Premium Anual",
    matriculas: 6,
    vigencia: "2026-09-10",
    status: "Ativo",
  },
  {
    id: "s3",
    nome: "Marcos Tavares",
    email: "marcos.tavares@gmail.com",
    cidade: "Canoas/RS",
    plano: "Avulso",
    matriculas: 2,
    vigencia: "2026-05-02",
    status: "Ativo",
  },
  {
    id: "s4",
    nome: "Felipe Nunes",
    email: "felipe.nunes@transmail.com",
    cidade: "Joinville/SC",
    plano: "Avulso",
    matriculas: 1,
    vigencia: "2026-04-18",
    status: "Inativo",
  },
  {
    id: "s5",
    nome: "Carla Menezes",
    email: "carla.menezes@oficinasul.com",
    cidade: "Porto Alegre/RS",
    plano: "Premium Anual",
    matriculas: 6,
    vigencia: "2027-01-05",
    status: "Ativo",
  },
  {
    id: "s6",
    nome: "Vagner Lima",
    email: "vagner@autolima.com.br",
    cidade: "Sapucaia/RS",
    plano: "Avulso",
    matriculas: 3,
    vigencia: "2026-06-30",
    status: "Ativo",
  },
];

const SEED_COURSES: AdminItem[] = [
  {
    id: "c1",
    titulo: "Fiat Dualogic — Diagnóstico e Reparo",
    sistema: "Automatizado",
    nivel: "Intermediário",
    preco: 397,
    precoAntigo: 597,
    horas: "8h40",
    aulas: 42,
    status: "Publicado",
  },
  {
    id: "c2",
    titulo: "Ford PowerShift — Embreagem Seca (DCT)",
    sistema: "Automatizado",
    nivel: "Avançado",
    preco: 447,
    precoAntigo: 647,
    horas: "9h05",
    aulas: 45,
    status: "Publicado",
  },
  {
    id: "c3",
    titulo: "VW iMotion — Fox e SpaceFox",
    sistema: "Automatizado",
    nivel: "Intermediário",
    preco: 347,
    precoAntigo: 497,
    horas: "6h10",
    aulas: 31,
    status: "Publicado",
  },
  {
    id: "c4",
    titulo: "GM Easytronic — Meriva e Corsa",
    sistema: "Automatizado",
    nivel: "Intermediário",
    preco: 347,
    precoAntigo: 497,
    horas: "5h50",
    aulas: 29,
    status: "Publicado",
  },
  {
    id: "c5",
    titulo: "DSG DQ200 / DQ250 — VW e Audi",
    sistema: "Dupla embreagem",
    nivel: "Avançado",
    preco: 497,
    precoAntigo: 747,
    horas: "11h20",
    aulas: 53,
    status: "Rascunho",
  },
  {
    id: "c6",
    titulo: "Câmbio Automático Convencional",
    sistema: "Automático",
    nivel: "Iniciante",
    preco: 397,
    precoAntigo: 547,
    horas: "8h25",
    aulas: 40,
    status: "Publicado",
  },
];

const SEED_TESTIMONIALS: AdminItem[] = [
  {
    id: "t1",
    nome: "Rogério Alves",
    papel: "Mecânico · Gravataí/RS",
    estrelas: 5,
    texto:
      "Parei de trocar peça no chute no Dualogic. Com o método fechei 3 câmbios na primeira semana e o cliente confia no laudo.",
    status: "Aprovado",
  },
  {
    id: "t2",
    nome: "Daniela Prado",
    papel: "Proprietária de oficina · Curitiba/PR",
    estrelas: 5,
    texto:
      "Coloquei dois funcionários no Premium. O nível técnico em automatizado subiu e os retrabalhos despencaram.",
    status: "Aprovado",
  },
  {
    id: "t3",
    nome: "Marcos Tavares",
    papel: "Mecânico autônomo · Canoas/RS",
    estrelas: 5,
    texto:
      "A didática da Rödelcar é de quem está na bancada todo dia. Os PDFs de calibração eu uso toda semana.",
    status: "Aprovado",
  },
  {
    id: "t4",
    nome: "Anderson Reis",
    papel: "Mecânico · Esteio/RS",
    estrelas: 4,
    texto:
      "Conteúdo muito bom de PowerShift. Senti falta de mais exemplos de EcoSport, mas o método resolve.",
    status: "Pendente",
  },
];

const SEED_PACKAGES: AdminItem[] = [
  {
    id: "p1",
    nome: "Formação Completa (Premium Anual)",
    preco: 1997,
    precoAntigo: 2929,
    parcelas: "12x de R$ 199,90",
    cursos: 6,
    status: "Ativo",
    inclui:
      "Todos os 6 cursos\nAtualizações na vigência\nComunidade fechada\nCertificado verificável\nBiblioteca de PDFs",
  },
  {
    id: "p2",
    nome: "Trilha Automatizados (Dualogic + iMotion + Easytronic)",
    preco: 897,
    precoAntigo: 1191,
    parcelas: "10x de R$ 89,70",
    cursos: 3,
    status: "Ativo",
    inclui:
      "3 cursos de automatizado\n1 ano de acesso\nComunidade fechada\nCertificado por curso",
  },
  {
    id: "p3",
    nome: "Curso Avulso (qualquer módulo)",
    preco: 397,
    precoAntigo: 597,
    parcelas: "12x de R$ 39,70",
    cursos: 1,
    status: "Ativo",
    inclui: "1 curso à escolha\n1 ano de acesso\nCertificado verificável",
  },
];

const SEED_ADMINS: AdminItem[] = [
  {
    id: "a1",
    nome: "Rödel",
    email: "rodel@rodelcar.com.br",
    papel: "Administrador",
    senha: "",
    ultimoAcesso: "hoje, 09:12",
    status: "Ativo",
  },
  {
    id: "a2",
    nome: "Patrícia Rödel",
    email: "patricia@rodelcar.com.br",
    papel: "Editor",
    senha: "",
    ultimoAcesso: "ontem, 17:40",
    status: "Ativo",
  },
  {
    id: "a3",
    nome: "Diego Souza",
    email: "diego.suporte@rodelcar.com.br",
    papel: "Suporte",
    senha: "",
    ultimoAcesso: "02/06, 11:05",
    status: "Ativo",
  },
];

export const ENTITY_KEYS: EntityKey[] = [
  "students",
  "courses",
  "testimonials",
  "packages",
  "admins",
];

export const ENTITIES: Record<EntityKey, EntitySchema> = {
  students: {
    label: "Alunos",
    singular: "aluno",
    icon: "users",
    seed: SEED_STUDENTS,
    title: (it) => String(it.nome),
    search: (it) => `${it.nome} ${it.email} ${it.cidade}`,
    filter: { key: "status", options: ["Todos", "Ativo", "Inativo"] },
    columns: [
      { key: "nome", label: "Aluno", kind: "user" },
      { key: "cidade", label: "Cidade" },
      { key: "plano", label: "Plano", kind: "badgePlan" },
      { key: "matriculas", label: "Cursos", kind: "center" },
      { key: "vigencia", label: "Vigência", kind: "date" },
      { key: "status", label: "Status", kind: "badgeStatus" },
    ],
    fields: [
      { key: "nome", label: "Nome completo", type: "text", col: "full" },
      { key: "email", label: "E-mail", type: "text" },
      { key: "cidade", label: "Cidade/UF", type: "text" },
      {
        key: "plano",
        label: "Plano",
        type: "select",
        options: ["Premium Anual", "Avulso"],
      },
      { key: "matriculas", label: "Cursos matriculados", type: "number" },
      { key: "vigencia", label: "Vigência até", type: "date" },
      {
        key: "status",
        label: "Aluno ativo",
        type: "toggle",
        on: "Ativo",
        off: "Inativo",
      },
    ],
    defaults: {
      nome: "",
      email: "",
      cidade: "",
      plano: "Avulso",
      matriculas: 1,
      vigencia: "2027-01-01",
      status: "Ativo",
    },
  },
  courses: {
    label: "Cursos",
    singular: "curso",
    icon: "book",
    seed: SEED_COURSES,
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
      { key: "preco", label: "Preço (R$)", type: "number" },
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
    seed: SEED_TESTIMONIALS,
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
    seed: SEED_PACKAGES,
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
      { key: "precoAntigo", label: "Preço antigo (R$)", type: "number" },
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
      precoAntigo: 1297,
      parcelas: "12x de R$ 99,70",
      cursos: 3,
      inclui: "",
      status: "Ativo",
    },
  },
  admins: {
    label: "Administradores",
    singular: "administrador",
    icon: "shield",
    seed: SEED_ADMINS,
    title: (it) => String(it.nome),
    search: (it) => `${it.nome} ${it.email} ${it.papel}`,
    filter: { key: "status", options: ["Todos", "Ativo", "Inativo"] },
    columns: [
      { key: "nome", label: "Usuário", kind: "user" },
      { key: "papel", label: "Papel", kind: "badgeRole" },
      { key: "ultimoAcesso", label: "Último acesso", kind: "muted" },
      { key: "status", label: "Status", kind: "badgeStatus" },
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
        key: "status",
        label: "Usuário ativo",
        type: "toggle",
        on: "Ativo",
        off: "Inativo",
      },
    ],
    defaults: {
      nome: "",
      email: "",
      papel: "Suporte",
      senha: "",
      ultimoAcesso: "nunca acessou",
      status: "Ativo",
    },
  },
};

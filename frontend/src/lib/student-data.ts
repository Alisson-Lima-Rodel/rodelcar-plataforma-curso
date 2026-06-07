/* Dados da Área do Aluno — RödelCar (placeholder realista, fase inicial).
   Trocar por fetch via TanStack Query quando o backend LMS expuser matrícula,
   progresso e certificados. */

export interface Student {
  name: string;
  first: string;
  initials: string;
  plan: string;
  daysLeft: number;
  expires: string;
}

export interface Kpi {
  label: string;
  value: string;
  sub: string;
  delta: string;
  trend: "up" | "flat";
  icon: string;
  spark: number[];
}

export interface Track {
  id: string;
  title: string;
  icon: string;
  done: number;
  total: number;
  pct: number;
  next: string;
  complete?: boolean;
}

export interface Resume {
  course: string;
  module: string;
  lesson: string;
  pct: number;
  time: string;
  left: string;
}

export type LessonState = "done" | "current" | "locked";

export interface PlayerLesson {
  t: string;
  dur: string;
  state: LessonState;
}

export interface PlayerModule {
  t: string;
  lessons: PlayerLesson[];
}

export interface Material {
  t: string;
  type: string;
  size: string;
  pages: number;
}

export interface QaItem {
  name: string;
  initials: string;
  time: string;
  text: string;
  replies: number;
  likes: number;
  instructor: boolean;
}

export interface Cert {
  course: string;
  student: string;
  date: string;
  hours: string;
  code: string;
  instructor: string;
}

export const STUDENT: Student = {
  name: "Rogério Alves",
  first: "Rogério",
  initials: "RA",
  plan: "Premium Anual",
  daysLeft: 47,
  expires: "23 jul 2026",
};

export const KPIS: Kpi[] = [
  {
    label: "Aulas concluídas",
    value: "128",
    sub: "de 236",
    delta: "+12 esta semana",
    trend: "up",
    icon: "checkCircle",
    spark: [3, 5, 4, 7, 6, 9, 8, 12],
  },
  {
    label: "Horas assistidas",
    value: "41h",
    sub: "tempo total",
    delta: "+3h20 esta semana",
    trend: "up",
    icon: "clock",
    spark: [4, 6, 5, 8, 7, 6, 9, 11],
  },
  {
    label: "Sequência",
    value: "9",
    sub: "dias seguidos",
    delta: "recorde: 14",
    trend: "flat",
    icon: "bolt",
    spark: [1, 1, 1, 1, 1, 1, 1, 1],
  },
  {
    label: "Certificados",
    value: "2",
    sub: "emitidos",
    delta: "1 em andamento",
    trend: "flat",
    icon: "award",
    spark: [0, 0, 1, 1, 1, 1, 2, 2],
  },
];

export const TRACKS: Track[] = [
  {
    id: "automatico",
    title: "Câmbio Automático Convencional",
    icon: "wrench",
    done: 38,
    total: 42,
    pct: 90,
    next: "Solenoides: teste e veredito",
  },
  {
    id: "dualogic",
    title: "Fiat Dualogic — Diagnóstico e Reparo",
    icon: "gauge",
    done: 24,
    total: 42,
    pct: 57,
    next: "Autoaprendizagem (PIS)",
  },
  {
    id: "imotion",
    title: "VW iMotion — Fox e SpaceFox",
    icon: "bolt",
    done: 31,
    total: 31,
    pct: 100,
    next: "Concluído",
    complete: true,
  },
  {
    id: "powershift",
    title: "Ford PowerShift — Embreagem Seca",
    icon: "infinity",
    done: 13,
    total: 45,
    pct: 29,
    next: "Embreagem seca: desgaste e troca",
  },
];

export const RESUME: Resume = {
  course: "Câmbio Automático Convencional",
  module: "Módulo 03 · Scanner e eletrônica",
  lesson: "Dados em tempo real que importam",
  pct: 64,
  time: "24:15",
  left: "8:47 restantes",
};

export const PLAYER_MODULES: PlayerModule[] = [
  {
    t: "Fundamentos do diagnóstico",
    lessons: [
      { t: "Como pensa um diagnosticista", dur: "12:40", state: "done" },
      { t: "Anatomia funcional do câmbio", dur: "18:05", state: "done" },
      { t: "Ferramentas e bancada mínima", dur: "09:30", state: "done" },
    ],
  },
  {
    t: "Pressão e hidráulica",
    lessons: [
      { t: "Pressão de linha na prática", dur: "22:10", state: "done" },
      { t: "Mapeando o corpo de válvulas", dur: "19:45", state: "done" },
      { t: "Falhas hidráulicas comuns", dur: "16:20", state: "done" },
    ],
  },
  {
    t: "Scanner e eletrônica",
    lessons: [
      { t: "Lendo códigos sem medo", dur: "20:00", state: "done" },
      { t: "Dados em tempo real que importam", dur: "24:15", state: "current" },
      { t: "Solenoides: teste e veredito", dur: "17:50", state: "locked" },
    ],
  },
  {
    t: "Laudo e road-test",
    lessons: [
      { t: "Checklist de road-test", dur: "14:30", state: "locked" },
      { t: "Montando o laudo técnico", dur: "15:10", state: "locked" },
      { t: "Apresentando o orçamento certo", dur: "11:25", state: "locked" },
    ],
  },
];

export const MATERIALS: Material[] = [
  {
    t: "Tabela de pressões de linha — referência",
    type: "PDF",
    size: "1.2 MB",
    pages: 8,
  },
  {
    t: "Mapa do corpo de válvulas (anotado)",
    type: "PDF",
    size: "3.4 MB",
    pages: 4,
  },
  {
    t: "Lista de códigos OBD-II por sintoma",
    type: "PDF",
    size: "820 KB",
    pages: 12,
  },
  {
    t: "Modelo de laudo técnico editável",
    type: "DOCX",
    size: "240 KB",
    pages: 2,
  },
];

export const QA: QaItem[] = [
  {
    name: "Daniela Prado",
    initials: "DP",
    time: "há 2 dias",
    text: "No teste de dados em tempo real, qual range de duty cycle do solenoide EPC vocês consideram normal em marcha lenta?",
    replies: 3,
    likes: 12,
    instructor: false,
  },
  {
    name: "Rödelcar",
    initials: "RC",
    time: "há 1 dia",
    text: "Boa pergunta, Daniela. Em marcha lenta espere algo entre 35–45%. Acima disso com temperatura normal, comece a suspeitar do circuito de pressão. Mostro um caso real na aula seguinte.",
    replies: 0,
    likes: 28,
    instructor: true,
  },
  {
    name: "Marcos Tavares",
    initials: "MT",
    time: "há 6 horas",
    text: "Salvou meu diagnóstico de ontem. Era exatamente o EPC fora de range. Cliente impressionado com o laudo!",
    replies: 1,
    likes: 9,
    instructor: false,
  },
];

export const CERT: Cert = {
  course: "VW iMotion — Fox e SpaceFox",
  student: "Rogério Alves",
  date: "02 de junho de 2026",
  hours: "6h10",
  code: "RC-2026-IMOT-8F3A1C",
  instructor: "Equipe Rödelcar",
};

/* Conteúdo do Portal — RödelCar (aterrissado no canal real @rodelcar.cambio)
   Rödelcar — Especializada em Câmbios Automáticos e Automatizados · Canoas-RS
   Sistemas: Dualogic, iMotion, Easytronic, PowerShift, DSG DQ200/DQ250, GSR
   + automático convencional.

   Fase inicial: conteúdo estático (placeholder realista). Quando o backend LMS
   expuser os cursos, trocar por fetch via TanStack Query mantendo estes tipos. */

export interface CourseModule {
  t: string;
  lessons: string[];
  dur: string[];
}

export interface Course {
  id: string;
  title: string;
  tagline: string;
  price: number;
  old?: number;
  hours: string;
  lessons: number;
  rating: number;
  students: number;
  level: string;
  icon: string;
  badge: { variant: string; label: string };
  desc?: string;
  learn?: string[];
  modules?: CourseModule[];
}

export interface Premium {
  title: string;
  price: number;
  old: number;
  installment: string;
  includes: string[];
}

export interface Video {
  t: string;
  dur: string;
  views: string;
}

export interface Testimonial {
  name: string;
  role: string;
  stars: number;
  text: string;
}

export interface Faq {
  q: string;
  a: string;
}

export const BRAND = {
  name: "RÖDELCAR",
  full: "Rödelcar — Especializada em Câmbios",
  city: "Canoas-RS",
  address: "Rua Esperança, 521 · Estância Velha · Canoas-RS · CEP 92030-500",
  channel: "@rodelcar.cambio",
  email: "taylormec.rs@gmail.com",
  whatsapp: "(51) 9574-0655",
  whatsappLink: "https://wa.me/555195740655",
  youtube: "https://www.youtube.com/@rodelcar.cambio",
  instagram: "https://www.instagram.com/rodelcar.cambios",
  threads: "https://www.threads.com/@rodelcar.cambios",
} as const;

export const COURSES: Course[] = [
  {
    id: "dualogic",
    title: "Fiat Dualogic — Diagnóstico e Reparo",
    tagline:
      "Punto, Linea, Stilo e Bravo: atuador, sangria e calibração sem chute.",
    price: 397,
    old: 597,
    hours: "8h40",
    lessons: 42,
    rating: 4.9,
    students: 1840,
    level: "Intermediário",
    icon: "gauge",
    badge: { variant: "", label: "Automatizado" },
    desc: "O câmbio automatizado mais comum nas oficinas brasileiras — e o que mais gera retrabalho quando diagnosticado no chute. Você aprende o método para atacar atuador, bomba, sangria e calibração com proxxon/scanner, isolando a falha real antes de abrir.",
    learn: [
      "Sangrar e calibrar o sistema Dualogic corretamente",
      "Diagnosticar o atuador (motor de embreagem e de marcha)",
      "Ler parâmetros do scanner que apontam a falha real",
      "Identificar desgaste de embreagem x falha hidráulica",
      "Procedimento de PIS / autoaprendizagem pós-reparo",
      "Montar laudo técnico e orçamento que o cliente aprova",
    ],
    modules: [
      {
        t: "Como funciona o Dualogic",
        lessons: [
          "Arquitetura do sistema",
          "Atuador, bomba e acumulador",
          "Ferramentas e bancada mínima",
        ],
        dur: ["12:40", "18:05", "09:30"],
      },
      {
        t: "Diagnóstico na prática",
        lessons: [
          "Lendo o scanner sem medo",
          "Sangria e pressão do sistema",
          "Embreagem: desgaste x hidráulica",
        ],
        dur: ["22:10", "19:45", "16:20"],
      },
      {
        t: "Reparo e atuador",
        lessons: [
          "Desmontagem do atuador",
          "Troca de embreagem e volante",
          "Vazamentos e selagem",
        ],
        dur: ["20:00", "24:15", "17:50"],
      },
      {
        t: "Calibração e entrega",
        lessons: [
          "Autoaprendizagem (PIS)",
          "Road-test com checklist",
          "Apresentando o orçamento certo",
        ],
        dur: ["14:30", "15:10", "11:25"],
      },
    ],
  },
  {
    id: "powershift",
    title: "Ford PowerShift — Embreagem Seca (DCT)",
    tagline: "Focus e EcoSport: por que a embreagem seca falha e como reparar.",
    price: 447,
    old: 647,
    hours: "9h05",
    lessons: 45,
    rating: 4.8,
    students: 1310,
    level: "Avançado",
    icon: "infinity",
    badge: { variant: "", label: "Automatizado" },
  },
  {
    id: "imotion",
    title: "VW iMotion — Fox e SpaceFox",
    tagline: "Atuador, calibração e as falhas que mais aparecem na bancada.",
    price: 347,
    old: 497,
    hours: "6h10",
    lessons: 31,
    rating: 4.9,
    students: 980,
    level: "Intermediário",
    icon: "bolt",
    badge: { variant: "", label: "Automatizado" },
  },
  {
    id: "easytronic",
    title: "GM Easytronic — Meriva e Corsa",
    tagline: "Domine o automatizado da GM: atuador, sensores e calibração.",
    price: 347,
    old: 497,
    hours: "5h50",
    lessons: 29,
    rating: 4.7,
    students: 760,
    level: "Intermediário",
    icon: "gauge",
    badge: { variant: "", label: "Automatizado" },
  },
  {
    id: "dsg",
    title: "DSG DQ200 / DQ250 — VW e Audi",
    tagline: "Dupla embreagem: mecatrônica, banho de óleo e seca na prática.",
    price: 497,
    old: 747,
    hours: "11h20",
    lessons: 53,
    rating: 5.0,
    students: 690,
    level: "Avançado",
    icon: "infinity",
    badge: { variant: "", label: "Dupla embreagem" },
  },
  {
    id: "automatico",
    title: "Câmbio Automático Convencional",
    tagline: "Hidráulico e eletrônico: pressão, conversor e scanner do zero.",
    price: 397,
    old: 547,
    hours: "8h25",
    lessons: 40,
    rating: 4.9,
    students: 2010,
    level: "Iniciante",
    icon: "wrench",
    badge: { variant: "", label: "Automático" },
  },
];

export const PREMIUM: Premium = {
  title: "Formação Completa em Câmbios Automáticos e Automatizados",
  price: 1997,
  old: 2929,
  installment: "12x de R$ 199,90",
  includes: [
    "Todos os 6 cursos: Dualogic, PowerShift, iMotion, Easytronic, DSG e automático",
    "Atualizações e novos sistemas durante a vigência",
    "Comunidade fechada de mecânicos + dúvidas direto com a Rödelcar",
    "Certificado verificável com código único",
    "Biblioteca de PDFs, calibrações e tabelas de torque",
  ],
};

export const VIDEOS: Video[] = [
  {
    t: "Fiat Dualogic dando trancos: o que checar primeiro",
    dur: "12:48",
    views: "84 mil",
  },
  {
    t: "Ford PowerShift: por que a embreagem seca falha",
    dur: "14:21",
    views: "127 mil",
  },
  {
    t: "VW iMotion no Fox: atuador e calibração passo a passo",
    dur: "18:05",
    views: "61 mil",
  },
];

export const TESTIMONIALS: Testimonial[] = [
  {
    name: "Rogério Alves",
    role: "Mecânico · Gravataí/RS",
    stars: 5,
    text: "Parei de trocar peça no chute no Dualogic. Com o método fechei 3 câmbios na primeira semana e o cliente confia no laudo. Mudou minha oficina.",
  },
  {
    name: "Daniela Prado",
    role: "Proprietária de oficina · Curitiba/PR",
    stars: 5,
    text: "Coloquei dois funcionários no Premium. O nível técnico em automatizado subiu e os retrabalhos despencaram. O acesso de um ano paga muito mais que o valor.",
  },
  {
    name: "Marcos Tavares",
    role: "Mecânico autônomo · Canoas/RS",
    stars: 5,
    text: "A didática da Rödelcar é de quem está na bancada todo dia. Sem enrolação, direto ao ponto. Os PDFs de calibração eu uso toda semana.",
  },
  {
    name: "Felipe Nunes",
    role: "Técnico em transmissões · Joinville/SC",
    stars: 5,
    text: "O curso de PowerShift clareou tudo sobre a embreagem seca. Hoje leio o scanner com confiança e fecho o orçamento certo de primeira.",
  },
];

export const FAQ: Faq[] = [
  {
    q: "Por quanto tempo tenho acesso?",
    a: "Cada compra dá 1 ano de acesso completo ao conteúdo, com todas as atualizações lançadas dentro do período de vigência.",
  },
  {
    q: "Os cursos cobrem câmbio automatizado e automático?",
    a: "Sim. A especialidade da Rödelcar são os automatizados — Dualogic, PowerShift, iMotion, Easytronic e DSG — além do câmbio automático convencional. A Formação Completa reúne todos.",
  },
  {
    q: "Preciso de ferramentas caras para acompanhar?",
    a: "Não. Mostramos a bancada mínima viável e como tirar o máximo do scanner e do multímetro que você já tem antes de investir em equipamento dedicado.",
  },
  {
    q: "A avaliação presencial é em Canoas?",
    a: "Sim. A oficina fica na Rua Esperança, 521 — Estância Velha, Canoas-RS. Você agenda a avaliação e recebe o laudo técnico do seu veículo.",
  },
  {
    q: "Como funciona o certificado?",
    a: "Ao concluir um curso você recebe um certificado com código único verificável — ideal para comprovar especialização para clientes e empregadores.",
  },
];

export function getCourse(id: string): Course | undefined {
  return COURSES.find((c) => c.id === id);
}

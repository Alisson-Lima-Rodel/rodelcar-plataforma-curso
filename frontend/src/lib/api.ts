/* Cliente HTTP do backend RödelCar. Centraliza a base URL e o envelope de erro
   padrão do contrato (`{ error: { code, message, details } }`). */

import type { Course, Faq, Testimonial, Video } from "./portal-data";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export interface ApiErrorEnvelope {
  error: { code: string; message: string; details: unknown };
}

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown;
  constructor(status: number, code: string, message: string, details: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK",
      "Não foi possível conectar ao servidor.",
      null,
    );
  }

  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!res.ok) {
    const env = data as ApiErrorEnvelope | null;
    const err = env?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "ERROR",
      err?.message ?? res.statusText,
      err?.details ?? null,
    );
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
};

// ── Leads (agendamento de avaliação) ──────────────────────────────────────────
export interface LeadInput {
  nome: string;
  telefone: string;
  email?: string;
  tipo_servico?: string;
  mensagem?: string;
  origem?: string;
}

export interface LeadCreated {
  id: string;
  status: string;
}

export function createLead(input: LeadInput): Promise<LeadCreated> {
  return api.post<LeadCreated>("/leads", input);
}

// ── Recuperação de senha (link gerado pelo admin) ─────────────────────────────
export function confirmarResetSenha(
  token: string,
  nova_senha: string,
): Promise<void> {
  return api.post<void>("/auth/recuperar-senha/confirmar", {
    token,
    nova_senha,
  });
}

// ── Cursos (vitrine pública / página de venda) ────────────────────────────────
// Server-side fetch (SSR). Em Docker, defina API_URL_INTERNAL=http://backend:8000/api/v1.
// `localhost` no loopback é forçado a IPv4 (127.0.0.1): em dev no Windows/Node o
// `localhost` resolve só para IPv6 (::1) e o uvicorn escuta em IPv4, o que faria
// TODO fetch SSR dar ECONNREFUSED (vitrine/vídeos/depoimentos sumiriam). Só afeta o
// fetch do SERVIDOR; o browser usa API_URL. Em prod a base é um domínio real (no-op).
const SERVER_API_URL = (
  process.env.API_URL_INTERNAL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1"
).replace(/\/\/localhost(?=[:/]|$)/, "//127.0.0.1");

interface ApiCourseBase {
  slug: string;
  titulo: string;
  tipo: string;
  preco: number;
  preco_antigo?: number | null;
  thumbnail_url?: string | null;
  tagline?: string | null;
  horas?: string | null;
  aulas_total: number;
  rating?: number | null;
  nivel?: string | null;
  icon?: string | null;
  badge_label?: string | null;
  gratuito?: boolean;
}

interface ApiCourseListItem extends ApiCourseBase {
  descricao_curta?: string | null;
  total_modulos: number;
  total_aulas: number;
  tem_preview?: boolean;
  destaque: boolean;
}

interface ApiCourseDetail extends ApiCourseBase {
  descricao?: string | null;
  aprende?: string[];
  idiomas_legenda?: string[];
  modulos: {
    id: string;
    titulo: string;
    ordem: number;
    total_aulas: number;
    aulas: {
      id: string;
      titulo: string;
      duracao_label: string;
      gratuita?: boolean;
    }[];
  }[];
}

function mapBase(
  c: ApiCourseBase & { descricao_curta?: string | null },
): Course {
  return {
    id: c.slug,
    title: c.titulo,
    tagline: c.tagline ?? c.descricao_curta ?? "",
    price: c.preco,
    old: c.preco_antigo ?? undefined,
    hours: c.horas ?? "",
    lessons: c.aulas_total,
    rating: c.rating ?? 0,
    level: c.nivel ?? "",
    icon: c.icon ?? "gauge",
    badge: { variant: "", label: c.badge_label ?? "" },
    cover: c.thumbnail_url ?? undefined,
    gratuito: !!c.gratuito,
  };
}

async function serverGet<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${SERVER_API_URL}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getCursos(): Promise<Course[]> {
  const data = await serverGet<{ items: ApiCourseListItem[] }>(
    "/cursos?size=100",
  );
  return (data?.items ?? []).map((c) => ({
    ...mapBase(c),
    hasPreview: !!c.tem_preview,
  }));
}

// ── Planos de assinatura (card Premium da vitrine) ────────────────────────────
export interface PlanoPublico {
  id: string;
  nome: string;
  intervalo: "mensal" | "anual" | string;
  preco: number;
}

export async function getPlanos(): Promise<PlanoPublico[]> {
  const data = await serverGet<PlanoPublico[]>("/planos");
  return data ?? [];
}

// ── Depoimentos (prova social pública) ────────────────────────────────────────
interface ApiDepoimento {
  nome: string;
  papel?: string | null;
  estrelas: number;
  texto: string;
}

export async function getDepoimentos(): Promise<Testimonial[]> {
  const data = await serverGet<ApiDepoimento[]>("/depoimentos");
  return (data ?? []).map((d) => ({
    name: d.nome,
    role: d.papel ?? "",
    stars: d.estrelas,
    text: d.texto,
  }));
}

// ── Vídeos (prova social) ─────────────────────────────────────────────────────
interface ApiVideo {
  titulo: string;
  youtube_url?: string | null;
  canal?: string | null;
  duracao?: string | null;
  views?: string | null;
  likes?: string | null;
  estrelas?: number | null;
}

export async function getVideos(): Promise<Video[]> {
  const data = await serverGet<ApiVideo[]>("/videos");
  return (data ?? []).map((v) => ({
    t: v.titulo,
    canal: v.canal ?? undefined,
    estrelas: v.estrelas ?? undefined,
    dur: v.duracao ?? "",
    views: v.views ?? "",
    likes: v.likes ?? undefined,
    url: v.youtube_url ?? undefined,
  }));
}

// ── FAQ (página de venda) ─────────────────────────────────────────────────────
interface ApiFaq {
  pergunta: string;
  resposta: string;
}

export async function getFaq(): Promise<Faq[]> {
  const data = await serverGet<ApiFaq[]>("/faq");
  return (data ?? []).map((f) => ({ q: f.pergunta, a: f.resposta }));
}

// ── Mídia das turmas presenciais (mosaico bento da home) ──────────────────────
interface ApiTurmaMidia {
  url: string;
  alt?: string | null;
  destaque?: boolean;
}

// Casa com o tipo `Photo` do componente <Turmas/> (compatível estruturalmente).
export interface TurmaFoto {
  src: string;
  span: "bento-wide" | "bento-tall";
  alt: string;
}

export async function getTurmasMidia(): Promise<TurmaFoto[]> {
  const data = await serverGet<ApiTurmaMidia[]>("/turmas-midia");
  return (data ?? []).map((m) => ({
    src: m.url,
    span: m.destaque ? "bento-wide" : "bento-tall",
    alt: m.alt ?? "",
  }));
}

// ── Avaliações públicas do curso (prova social + aggregateRating) ─────────────
export interface AvaliacaoPublica {
  autor: string;
  nota: number;
  texto: string | null;
  criado_em: string;
}

export interface AvaliacoesCurso {
  items: AvaliacaoPublica[];
  media: number | null;
  total: number;
}

export async function getAvaliacoes(slug: string): Promise<AvaliacoesCurso> {
  const data = await serverGet<AvaliacoesCurso>(
    `/cursos/${encodeURIComponent(slug)}/avaliacoes`,
  );
  return data ?? { items: [], media: null, total: 0 };
}

// ── Avaliações do Google (ficha do Google Business) ───────────────────────────
export interface GoogleReviewItem {
  autor: string | null;
  nota: number | null;
  texto: string | null;
  quando: string | null;
}

export interface GoogleReviews {
  rating: number | null;
  total: number;
  reviews: GoogleReviewItem[];
}

export async function getGoogleReviews(): Promise<GoogleReviews> {
  const data = await serverGet<GoogleReviews>("/google-reviews");
  return data ?? { rating: null, total: 0, reviews: [] };
}

// ── Verificação pública de certificado ────────────────────────────────────────
export interface CertificadoVerificado {
  valido: boolean;
  aluno_nome: string;
  curso: string;
  emitido_em: string;
}

export async function verificarCertificado(
  codigo: string,
): Promise<CertificadoVerificado | null> {
  return serverGet<CertificadoVerificado>(
    `/certificados/${encodeURIComponent(codigo)}/verificar`,
  );
}

export async function getCurso(slug: string): Promise<Course | null> {
  const d = await serverGet<ApiCourseDetail>(
    `/cursos/${encodeURIComponent(slug)}`,
  );
  if (!d) return null;
  return {
    ...mapBase(d),
    hasPreview: (d.modulos ?? []).some((m) => m.aulas.some((a) => a.gratuita)),
    desc: d.descricao ?? undefined,
    learn: d.aprende ?? [],
    idiomasLegenda: d.idiomas_legenda ?? [],
    modules: (d.modulos ?? []).map((m) => ({
      t: m.titulo,
      lessons: m.aulas.map((a) => a.titulo),
      dur: m.aulas.map((a) => a.duracao_label),
    })),
  };
}

/* Autenticação + endpoints do aluno (🔒). Guarda os tokens no localStorage,
   manda o Bearer e renova o access automaticamente no 401 (rotação). */

import { ApiError, API_URL, type ApiErrorEnvelope } from "./api";

const ACCESS_KEY = "rodelcar_access";
const REFRESH_KEY = "rodelcar_refresh";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}
function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}
export function clearTokens() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const err = (data as ApiErrorEnvelope | null)?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "ERROR",
      err?.message ?? res.statusText,
      err?.details ?? null,
    );
  }
  return data as T;
}

export async function login(email: string, senha: string): Promise<void> {
  const t = await postJson<TokenResponse>("/auth/login", { email, senha });
  setTokens(t.access_token, t.refresh_token);
}

export async function register(
  nome: string,
  email: string,
  senha: string,
  codigoIndicacao?: string | null,
): Promise<void> {
  const t = await postJson<TokenResponse>("/auth/register", {
    nome,
    email,
    senha,
    codigo_indicacao: codigoIndicacao || undefined,
  });
  setTokens(t.access_token, t.refresh_token);
}

async function tryRefresh(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  try {
    const t = await postJson<TokenResponse>("/auth/refresh", {
      refresh_token: refresh,
    });
    setTokens(t.access_token, t.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export async function logout(): Promise<void> {
  const refresh =
    typeof window !== "undefined" ? localStorage.getItem(REFRESH_KEY) : null;
  clearTokens();
  if (refresh) {
    try {
      await postJson("/auth/logout", { refresh_token: refresh });
    } catch {
      /* logout é best-effort */
    }
  }
}

/** GET autenticado, com 1 retry após renovar o access token no 401. */
async function authGet<T>(path: string, retry = true): Promise<T> {
  const token = getAccessToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK",
      "Não foi possível conectar ao servidor.",
      null,
    );
  }
  if (res.status === 401 && retry && (await tryRefresh())) {
    return authGet<T>(path, false);
  }
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const err = (data as ApiErrorEnvelope | null)?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "ERROR",
      err?.message ?? res.statusText,
      err?.details ?? null,
    );
  }
  return data as T;
}

/** POST autenticado (mutação), com 1 retry após renovar o access no 401. */
async function authPost<T>(
  path: string,
  body?: unknown,
  retry = true,
): Promise<T> {
  const token = getAccessToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK",
      "Não foi possível conectar ao servidor.",
      null,
    );
  }
  if (res.status === 401 && retry && (await tryRefresh())) {
    return authPost<T>(path, body, false);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!res.ok) {
    const err = (data as ApiErrorEnvelope | null)?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "ERROR",
      err?.message ?? res.statusText,
      err?.details ?? null,
    );
  }
  return data as T;
}

// ── Tipos das respostas ───────────────────────────────────────────────────────
export interface Me {
  id: string;
  nome: string;
  email: string;
  matriculas_ativas: number;
}

export interface DashboardData {
  ultima_aula: {
    aula_id: string;
    titulo: string;
    curso_slug: string;
    percentual: number;
  } | null;
  alertas: { tipo: string; nivel: string; mensagem: string }[];
  resumo: {
    cursos_ativos: number;
    aulas_concluidas: number;
    certificados: number;
  };
}

export interface MatriculaItem {
  id: string;
  curso: { id: string; slug: string; titulo: string };
  status: string;
  data_inicio: string;
  data_expiracao: string;
  dias_restantes: number;
  progresso_percentual: number;
  // Direito de arrependimento (7 dias da compra)
  origem: "avulsa" | "assinatura" | "manual";
  cancelavel: boolean;
  cancelavel_ate: string | null;
  motivo_bloqueio: "RECURSO_CONSUMIDO" | "LIMITE_REEMBOLSOS" | null;
}

export interface CancelamentoResultado {
  matricula_id: string;
  reembolsado: boolean;
  assinatura_cancelada: boolean;
  cursos_revogados: number;
}

export interface AulaMaterial {
  id: string;
  nome: string;
  url_pdf: string;
}

export interface AulaDetail {
  id: string;
  titulo: string;
  modulo_id: string;
  panda_video_id: string | null;
  duracao_segundos: number;
  materiais: AulaMaterial[];
  progresso: {
    concluida: boolean;
    percentual: number;
    posicao_segundos: number;
  };
  player_token?: string | null;
  drm_group_id?: string | null;
}

export interface PlayerAula {
  id: string;
  titulo: string;
  duracao_label: string;
  concluida: boolean;
  percentual: number;
}

export interface PlayerQuizResumo {
  id: string;
  titulo: string;
  aprovado: boolean;
}

export interface PlayerModulo {
  id: string;
  titulo: string;
  ordem: number;
  aulas: PlayerAula[];
  quiz: PlayerQuizResumo | null;
}

export interface PlayerCurso {
  matricula_id: string;
  curso: { id: string; slug: string; titulo: string };
  horas: string | null;
  status: string;
  progresso_percentual: number;
  concluido: boolean;
  certificado: { codigo: string; emitido_em: string } | null;
  modulos: PlayerModulo[];
}

export interface CertificadoEmitido {
  id: string;
  codigo_verificacao: string;
  emitido_em: string;
}

export const getMe = () => authGet<Me>("/auth/me");
export const getDashboard = () => authGet<DashboardData>("/me/dashboard");
export const getMatriculas = () =>
  authGet<{ items: MatriculaItem[] }>("/me/matriculas");

export const getCursoPlayer = (slug: string) =>
  authGet<PlayerCurso>(`/me/cursos/${encodeURIComponent(slug)}`);
export const getAula = (aulaId: string) =>
  authGet<AulaDetail>(`/aulas/${aulaId}`);

export const salvarProgresso = (
  aula_id: string,
  percentual: number,
  concluida: boolean,
  posicao_segundos?: number,
) =>
  authPost<{ curso_percentual: number; posicao_segundos: number }>(
    "/progresso",
    {
      aula_id,
      percentual,
      concluida,
      // Omitido quando undefined → o backend preserva a posição (ex.: botão
      // "Concluir" não deve zerar onde o aluno parou).
      ...(posicao_segundos != null ? { posicao_segundos } : {}),
    },
  );

export const emitirCertificado = (matriculaId: string) =>
  authPost<CertificadoEmitido>(`/certificados/${matriculaId}`);

/** Cancela a compra dentro dos 7 dias (reembolso integral via Stripe). */
export const cancelarMatricula = (matriculaId: string) =>
  authPost<CancelamentoResultado>(`/me/matriculas/${matriculaId}/cancelar`);

/** Baixa o PDF do certificado (autenticado). Faz 1 retry após renovar no 401. */
export async function baixarCertificadoPdf(matriculaId: string): Promise<Blob> {
  const buscar = (token: string | null) =>
    fetch(`${API_URL}/certificados/${matriculaId}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  let res: Response;
  try {
    res = await buscar(getAccessToken());
    if (res.status === 401 && (await tryRefresh())) {
      res = await buscar(getAccessToken());
    }
  } catch {
    throw new ApiError(
      0,
      "NETWORK",
      "Não foi possível conectar ao servidor.",
      null,
    );
  }
  if (!res.ok) {
    throw new ApiError(
      res.status,
      "ERROR",
      "Falha ao baixar o certificado.",
      null,
    );
  }
  return res.blob();
}

/** Envia o link de verificação do certificado pelo WhatsApp do aluno. */
export const enviarCertificadoWhatsapp = (matriculaId: string) =>
  authPost<{ enviado: boolean }>(
    `/certificados/${matriculaId}/enviar-whatsapp`,
  );

// ── Avaliações (review do curso) ──────────────────────────────────────────────
export interface MinhaAvaliacao {
  nota: number;
  texto: string | null;
  status: string;
}

export const getMinhaAvaliacao = (slug: string) =>
  authGet<MinhaAvaliacao | null>(
    `/cursos/${encodeURIComponent(slug)}/avaliacoes/minha`,
  );

export const enviarAvaliacao = (
  slug: string,
  nota: number,
  texto: string | null,
) =>
  authPost<MinhaAvaliacao>(`/cursos/${encodeURIComponent(slug)}/avaliacoes`, {
    nota,
    texto,
  });

// ── Aula grátis (preview) — exige login (captura o lead) ──────────────────────
export interface AulaPreview {
  id: string;
  titulo: string;
  panda_video_id: string | null;
  player_token?: string | null;
  drm_group_id?: string | null;
}

export const getPreview = (slug: string) =>
  authGet<AulaPreview[]>(`/cursos/${encodeURIComponent(slug)}/preview`);

// ── Matrícula gratuita (curso marcado como gratuito) ──────────────────────────
export interface MatriculaGratis {
  matricula_id: string;
  slug: string;
  status: string;
  ja_matriculado: boolean;
}

export const matricularGratis = (slug: string) =>
  authPost<MatriculaGratis>(
    `/me/matriculas/gratis/${encodeURIComponent(slug)}`,
  );

// ── Indique e ganhe (referral) ────────────────────────────────────────────────
export interface CupomGanho {
  codigo: string;
  tipo: string;
  valor: number;
  validade: string | null;
}

export interface Indicacoes {
  codigo: string;
  total_indicados: number;
  total_recompensados: number;
  cupons: CupomGanho[];
}

export const getIndicacoes = () => authGet<Indicacoes>("/me/indicacoes");

// ── Quiz (aluno) ──────────────────────────────────────────────────────────────
export interface QuizAlternativa {
  id: string;
  texto: string;
}
export interface QuizQuestao {
  id: string;
  enunciado: string;
  alternativas: QuizAlternativa[];
}
export interface QuizAluno {
  id: string;
  titulo: string;
  nota_corte: number;
  aprovado: boolean;
  melhor_nota: number | null;
  questoes: QuizQuestao[];
}
export interface QuizResultado {
  nota: number;
  aprovado: boolean;
  corretas: number;
  total: number;
}

export const getQuiz = (quizId: string) =>
  authGet<QuizAluno>(`/quizzes/${quizId}`);

export const responderQuiz = (
  quizId: string,
  respostas: { questao_id: string; alternativa_id: string }[],
) => authPost<QuizResultado>(`/quizzes/${quizId}/tentativas`, { respostas });

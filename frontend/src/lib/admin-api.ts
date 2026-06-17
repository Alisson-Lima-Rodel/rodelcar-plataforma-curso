/* Camada de API do painel admin. Token próprio (separado do aluno), Bearer e
   CRUD genérico por entidade. No 401 o caller redireciona pro login. */

import { ApiError, API_URL, type ApiErrorEnvelope } from "./api";

const ADMIN_KEY = "rodelcar_admin_access";

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_KEY);
}
function setAdminToken(t: string) {
  localStorage.setItem(ADMIN_KEY, t);
}
export function clearAdminToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ADMIN_KEY);
}

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAdminToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK",
      "Não foi possível conectar ao servidor.",
      null,
    );
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

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface AdminMe {
  id: string;
  nome: string;
  email: string;
  papel: string;
}

export async function adminLogin(email: string, senha: string): Promise<void> {
  const t = await adminFetch<{ access_token: string }>("/admin/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
  setAdminToken(t.access_token);
}

/** Logout: limpa o token local E revoga a sessão no servidor (o backend bumpa
 * o token_version, matando qualquer access token vivo — token roubado para de
 * valer). Best-effort: a UI desloga na hora mesmo se a rede falhar. O token é
 * capturado ANTES da limpeza porque a rota exige Bearer. */
export async function adminLogout(): Promise<void> {
  const token = getAdminToken();
  clearAdminToken();
  if (!token) return;
  try {
    await fetch(`${API_URL}/admin/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      keepalive: true,
    });
  } catch {
    /* logout é best-effort */
  }
}

export const getAdminMe = () => adminFetch<AdminMe>("/admin/auth/me");

// ── Upload de imagem (capa de curso) ──────────────────────────────────────────
/** Sobe a imagem ao backend (Supabase Storage) e retorna a URL pública. */
export async function uploadImagem(file: File): Promise<string> {
  const token = getAdminToken();
  const fd = new FormData();
  fd.append("arquivo", file);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/admin/uploads/imagem`, {
      method: "POST",
      // NÃO setar Content-Type: o browser define o boundary do multipart.
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
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
    const err = (data as ApiErrorEnvelope | null)?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "ERROR",
      err?.message ?? res.statusText,
      err?.details ?? null,
    );
  }
  return (data as { url: string }).url;
}

// ── Reembolsos (suporte) ──────────────────────────────────────────────────────
export interface ReembolsoItem {
  matricula_id: string;
  curso_titulo: string;
  status: string;
  origem: "avulsa" | "assinatura" | "manual";
  valor: number | null;
  pago_em: string | null;
  dentro_da_janela: boolean;
  cancelavel: boolean;
}

export interface AlunoReembolsos {
  aluno_id: string;
  nome: string;
  email: string;
  matriculas: ReembolsoItem[];
}

export interface CancelamentoAdmin {
  matricula_id: string;
  reembolsado: boolean;
  assinatura_cancelada: boolean;
  cursos_revogados: number;
}

export const buscarReembolsos = (email: string) =>
  adminFetch<AlunoReembolsos>(
    `/admin/reembolsos?email=${encodeURIComponent(email)}`,
  );

export const cancelarMatriculaAdmin = (matriculaId: string) =>
  adminFetch<CancelamentoAdmin>(`/admin/reembolsos/${matriculaId}/cancelar`, {
    method: "POST",
  });

// ── Moderação de avaliações ───────────────────────────────────────────────────
export interface AvaliacaoAdmin {
  id: string;
  aluno_nome: string;
  curso_titulo: string;
  nota: number;
  texto: string | null;
  status: string; // "Aprovado" | "Pendente"
  criado_em: string;
}

export const buscarAvaliacoes = () =>
  adminFetch<AvaliacaoAdmin[]>("/admin/avaliacoes");

export const moderarAvaliacao = (id: string, status: "Aprovado" | "Pendente") =>
  adminFetch<AvaliacaoAdmin>(`/admin/avaliacoes/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

export const excluirAvaliacao = (id: string) =>
  adminFetch<void>(`/admin/avaliacoes/${id}`, { method: "DELETE" });

// ── Conteúdo do curso (módulos / aulas) ───────────────────────────────────────
export interface AdminAula {
  id: string;
  titulo: string;
  panda_video_id: string | null;
  duracao_segundos: number;
  ordem: number;
  gratuita: boolean;
}

export interface AdminModulo {
  id: string;
  titulo: string;
  ordem: number;
  aulas: AdminAula[];
}

export const listarConteudo = (cursoId: string) =>
  adminFetch<AdminModulo[]>(`/admin/cursos/${cursoId}/conteudo`);

export const criarModulo = (cursoId: string, data: Record<string, unknown>) =>
  adminFetch<AdminModulo>(`/admin/cursos/${cursoId}/modulos`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const atualizarModulo = (id: string, data: Record<string, unknown>) =>
  adminFetch<AdminModulo>(`/admin/modulos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const excluirModulo = (id: string) =>
  adminFetch<void>(`/admin/modulos/${id}`, { method: "DELETE" });

export const criarAula = (moduloId: string, data: Record<string, unknown>) =>
  adminFetch<AdminAula>(`/admin/modulos/${moduloId}/aulas`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const atualizarAula = (id: string, data: Record<string, unknown>) =>
  adminFetch<AdminAula>(`/admin/aulas/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const excluirAula = (id: string) =>
  adminFetch<void>(`/admin/aulas/${id}`, { method: "DELETE" });

// ── Upload de vídeo (Panda) pela tela admin ───────────────────────────────────
export interface AulaUploadInfo {
  video_id: string;
  upload_url: string;
}
export interface AulaSyncInfo {
  panda_video_id: string | null;
  status: string | null;
  duracao_segundos: number;
  thumbnail: string | null;
}

/** 1) Backend cria a sessão de upload no Panda e grava o video_id na aula. */
export const gerarUploadAula = (
  aulaId: string,
  body: { filename: string; size: number; content_type?: string },
) =>
  adminFetch<AulaUploadInfo>(`/admin/aulas/${aulaId}/upload-url`, {
    method: "POST",
    body: JSON.stringify(body),
  });

/** 3) Puxa duração/capa/status do Panda e preenche a aula. */
export const sincronizarAulaPanda = (aulaId: string) =>
  adminFetch<AulaSyncInfo>(`/admin/aulas/${aulaId}/sync-panda`, {
    method: "POST",
  });

// ── Analytics de retenção (Panda) ─────────────────────────────────────────────
export interface RetencaoPonto {
  segundo: number;
  percentual: number;
}
export interface RetencaoInfo {
  panda_video_id: string;
  duracao_segundos: number | null;
  pontos: RetencaoPonto[];
}
export const retencaoAula = (aulaId: string) =>
  adminFetch<RetencaoInfo>(`/admin/aulas/${aulaId}/retencao`);

// ── Biblioteca do Panda (selecionar um vídeo já existente) ────────────────────
export interface PandaVideoItem {
  id: string;
  titulo: string;
  duracao_segundos: number | null;
  thumbnail: string | null;
  status: string | null;
}
export interface PandaBiblioteca {
  itens: PandaVideoItem[];
  page: number;
  limit: number;
}
export interface PandaPasta {
  id: string;
  nome: string;
}

/** Lista a biblioteca da conta no Panda (mediado pelo backend). */
export const listarVideosPanda = (
  params: {
    title?: string;
    folder_id?: string;
    page?: number;
    limit?: number;
  } = {},
) => {
  const qs = new URLSearchParams();
  if (params.title) qs.set("title", params.title);
  if (params.folder_id) qs.set("folder_id", params.folder_id);
  if (params.page) qs.set("page", String(params.page));
  if (params.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return adminFetch<PandaBiblioteca>(`/admin/panda/videos${q ? `?${q}` : ""}`);
};

/** Pastas da conta no Panda, para filtrar a biblioteca. */
export const listarPastasPanda = () =>
  adminFetch<{ itens: PandaPasta[] }>(`/admin/panda/pastas`);

/** 2) Sobe o arquivo direto para o Panda (PATCH TUS na URL pré-autorizada).
 * Vai direto ao uploader do Panda — sem Bearer, sem a PANDA_API_KEY no browser. */
export function enviarVideoPanda(
  uploadUrl: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PATCH", uploadUrl, true);
    xhr.setRequestHeader("Tus-Resumable", "1.0.0");
    xhr.setRequestHeader("Upload-Offset", "0");
    xhr.setRequestHeader("Content-Type", "application/offset+octet-stream");
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable)
          onProgress(Math.round((e.loaded / e.total) * 100));
      };
    }
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new Error(`Upload falhou (${xhr.status})`));
    xhr.onerror = () => reject(new Error("Erro de rede no upload"));
    xhr.send(file);
  });
}

// ── Quiz do módulo (com gabarito) ─────────────────────────────────────────────
export interface AdminAlternativa {
  id?: string;
  texto: string;
  correta: boolean;
}
export interface AdminQuestao {
  id?: string;
  enunciado: string;
  alternativas: AdminAlternativa[];
}
export interface AdminQuiz {
  id: string;
  modulo_id: string;
  titulo: string;
  nota_corte: number;
  ativo: boolean;
  questoes: AdminQuestao[];
}

export const getQuizAdmin = (moduloId: string) =>
  adminFetch<AdminQuiz | null>(`/admin/modulos/${moduloId}/quiz`);

export const salvarQuiz = (
  moduloId: string,
  data: {
    titulo: string;
    nota_corte: number;
    ativo: boolean;
    questoes: AdminQuestao[];
  },
) =>
  adminFetch<AdminQuiz>(`/admin/modulos/${moduloId}/quiz`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const excluirQuiz = (moduloId: string) =>
  adminFetch<void>(`/admin/modulos/${moduloId}/quiz`, { method: "DELETE" });

// ── CRUD genérico ─────────────────────────────────────────────────────────────
export type AdminRow = Record<string, unknown> & { id: string };

export function adminCrud(path: string) {
  return {
    list: () => adminFetch<AdminRow[]>(path),
    create: (data: Record<string, unknown>) =>
      adminFetch<AdminRow>(path, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Record<string, unknown>) =>
      adminFetch<AdminRow>(`${path}/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    remove: (id: string) =>
      adminFetch<void>(`${path}/${id}`, { method: "DELETE" }),
  };
}

export type AdminCrud = ReturnType<typeof adminCrud>;

export const ADMIN_CRUD: Record<string, AdminCrud> = {
  students: adminCrud("/admin/alunos"),
  courses: adminCrud("/admin/cursos"),
  testimonials: adminCrud("/admin/depoimentos"),
  plans: adminCrud("/admin/planos"),
  cupons: adminCrud("/admin/cupons"),
  videos: adminCrud("/admin/videos"),
  faq: adminCrud("/admin/faqs"),
  admins: adminCrud("/admin/administradores"),
};

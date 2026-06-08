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
): Promise<void> {
  const t = await postJson<TokenResponse>("/auth/register", {
    nome,
    email,
    senha,
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
}

export const getMe = () => authGet<Me>("/auth/me");
export const getDashboard = () => authGet<DashboardData>("/me/dashboard");
export const getMatriculas = () =>
  authGet<{ items: MatriculaItem[] }>("/me/matriculas");

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

export function adminLogout() {
  clearAdminToken();
}

export const getAdminMe = () => adminFetch<AdminMe>("/admin/auth/me");

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
  videos: adminCrud("/admin/videos"),
  faq: adminCrud("/admin/faqs"),
  admins: adminCrud("/admin/administradores"),
};

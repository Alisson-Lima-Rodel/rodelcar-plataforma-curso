/* Cliente HTTP do backend RödelCar. Centraliza a base URL e o envelope de erro
   padrão do contrato (`{ error: { code, message, details } }`). */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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
    throw new ApiError(0, "NETWORK", "Não foi possível conectar ao servidor.", null);
  }

  const text = await res.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!res.ok) {
    const env = data as ApiErrorEnvelope | null;
    const err = env?.error;
    throw new ApiError(res.status, err?.code ?? "ERROR", err?.message ?? res.statusText, err?.details ?? null);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) }),
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

/** Cliente HTTP da API. Todas as chamadas passam por aqui. */

export type ApiErrorBody = {
  error?: { code: string; message: string; request_id?: string; details?: unknown };
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly requestId?: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!resp.ok) {
    let body: ApiErrorBody | undefined;
    try {
      body = (await resp.json()) as ApiErrorBody;
    } catch {
      body = undefined;
    }
    throw new ApiError(
      resp.status,
      body?.error?.code ?? "erro_http",
      body?.error?.message ?? resp.statusText,
      body?.error?.request_id,
    );
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

// ------------------------------------------------------------------ saúde

export type Readiness = {
  status: "ok" | "falha";
  checks: Record<string, "ok" | "falha">;
};

export const getReadiness = () => apiFetch<Readiness>("/api/v1/health/ready");

// ------------------------------------------------------------------ autenticação

export type Papel = "admin" | "analista" | "validador" | "gestor_conhecimento";

export type Usuario = {
  id: string;
  email: string;
  nome: string;
  papeis: Papel[];
};

export type Provedores = { local: boolean; oidc: boolean };

export const getProvedores = () => apiFetch<Provedores>("/api/v1/auth/providers");

/** Usuário logado, ou `null` se não houver sessão válida. */
export async function getMe(): Promise<Usuario | null> {
  try {
    return await apiFetch<Usuario>("/api/v1/auth/me");
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
}

export const login = (email: string, senha: string) =>
  apiFetch<Usuario>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });

export const logout = () => apiFetch<void>("/api/v1/auth/logout", { method: "POST" });

/** Cliente HTTP da API. Todas as chamadas passam por aqui. */

export type ApiErrorBody = {
  error: { code: string; message: string; request_id?: string; details?: unknown };
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

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
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
      body?.error.code ?? "erro_http",
      body?.error.message ?? resp.statusText,
      body?.error.request_id,
    );
  }
  return (await resp.json()) as T;
}

export type Readiness = {
  status: "ok" | "falha";
  checks: Record<string, "ok" | "falha">;
};

export const getReadiness = () => apiFetch<Readiness>("/api/v1/health/ready");

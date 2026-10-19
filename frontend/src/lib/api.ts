// Wrapper de fetch para a API Flask. Sempre credentials: "include", para que o
// cookie de sessao do Flask-Login acompanhe a requisicao. Todas as chamadas
// saem do navegador (localhost nao alcanca o backend de dentro do container).
const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000"}/api`;

export class ApiError extends Error {
  status: number;
  code?: string;
  fields?: string[];

  constructor(status: number, message: string, code?: string, fields?: string[]) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const hasBody = init.body !== undefined;
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method: init.method ?? "GET",
      credentials: "include",
      headers: hasBody ? { "Content-Type": "application/json" } : undefined,
      body: hasBody ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Não foi possível falar com o servidor");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, data.message ?? "Erro inesperado", data.code, data.fields);
  }
  return data as T;
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Erro inesperado";
}

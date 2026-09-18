// Lightweight API client. Token is kept in localStorage (never committed).
const TOKEN_KEY = "recoverai_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  window.localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`/api/v1${path}`, { ...opts, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) => request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(p: string, body?: unknown) => request<T>(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(p: string) => request<T>(p, { method: "DELETE" }),
};

export function fmt(n: number | null | undefined, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(n ?? 0);
}
export function pct(n: number | null | undefined): string {
  return `${(((n ?? 0)) * 100).toFixed(1)}%`;
}

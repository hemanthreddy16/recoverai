// Lightweight API client. Token and optional backend override are kept in localStorage.
const TOKEN_KEY = "resurge_token";
const BACKEND_OVERRIDE_KEY = "resurge_backend_url";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export function sanitizeApiUrl(url: string | null | undefined): string {
  if (!url) return "";
  let clean = url.trim().replace(/\/+$/, "");
  // Ignore placeholder text like <your-backend-service-name>
  if (clean.includes("<") || clean.includes(">") || clean.includes("your-backend-service-name")) {
    return "";
  }
  if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
    clean = clean.includes("localhost") || clean.includes("127.0.0.1") ? `http://${clean}` : `https://${clean}`;
  }
  try {
    const parsed = new URL(clean);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return "";
    return clean;
  } catch {
    return "";
  }
}

export function getCustomBackendUrl(): string | null {
  if (typeof window === "undefined") return null;
  const custom = window.localStorage.getItem(BACKEND_OVERRIDE_KEY);
  return sanitizeApiUrl(custom) || null;
}

export function setCustomBackendUrl(url: string | null) {
  if (typeof window === "undefined") return;
  if (!url || !url.trim()) {
    window.localStorage.removeItem(BACKEND_OVERRIDE_KEY);
  } else {
    const clean = sanitizeApiUrl(url);
    if (clean) {
      window.localStorage.setItem(BACKEND_OVERRIDE_KEY, clean);
    } else {
      window.localStorage.removeItem(BACKEND_OVERRIDE_KEY);
    }
  }
}

export function getEffectiveApiBase(): string {
  if (typeof window !== "undefined") {
    const custom = window.localStorage.getItem(BACKEND_OVERRIDE_KEY);
    if (custom) {
      const sanitized = sanitizeApiUrl(custom);
      if (sanitized) return sanitized;
      window.localStorage.removeItem(BACKEND_OVERRIDE_KEY);
    }
  }

  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim()) {
    const sanitized = sanitizeApiUrl(envUrl);
    if (sanitized) return sanitized;
  }

  return "";
}

export class ApiError extends Error {
  status: number;
  data?: any;
  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const base = getEffectiveApiBase();
  const url = base ? `${base}/api/v1${path}` : `/api/v1${path}`;

  let res: Response;
  try {
    res = await fetch(url, { ...opts, headers });
  } catch (err: any) {
    throw new ApiError(
      0,
      `Network connection failed to ${url}. Please verify your backend service is running and accessible: ${err?.message || "Connection refused"}`
    );
  }

  if (res.status === 401) {
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      clearToken();
      window.location.href = "/login";
    }
    const text = await res.text().catch(() => "");
    let msg = "Invalid email or password";
    try {
      const data = JSON.parse(text);
      if (data.detail) msg = data.detail;
    } catch {}
    throw new ApiError(401, msg);
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let msg = text || res.statusText;
    let parsedData: any = null;
    try {
      parsedData = JSON.parse(text);
      if (parsedData.detail) {
        msg = typeof parsedData.detail === "string" ? parsedData.detail : JSON.stringify(parsedData.detail);
      }
    } catch {}
    throw new ApiError(res.status, msg, parsedData);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(p: string) => request<T>(p, { method: "DELETE" }),

  checkHealth: async (baseUrl?: string): Promise<{ ok: boolean; message: string; data?: any }> => {
    const base = (baseUrl || getEffectiveApiBase() || "").replace(/\/+$/, "");
    const target = base ? `${base}/health` : `/health`;
    try {
      const res = await fetch(target);
      if (res.ok) {
        const data = await res.json();
        return { ok: true, message: `Connected to ${target}`, data };
      }
      return { ok: false, message: `Server returned HTTP ${res.status}: ${res.statusText}` };
    } catch (e: any) {
      return { ok: false, message: `Cannot connect to ${target}: ${e.message || "Connection refused"}` };
    }
  },
};

export function fmt(n: number | null | undefined, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(n ?? 0);
}

export function pct(n: number | null | undefined): string {
  return `${((n ?? 0) * 100).toFixed(1)}%`;
}

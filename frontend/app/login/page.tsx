"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Settings, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import {
  api,
  setToken,
  ApiError,
  getEffectiveApiBase,
  getCustomBackendUrl,
  setCustomBackendUrl,
} from "@/lib/api";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");

  // Login fields
  const [email, setEmail] = useState("demo@recoverai.dev");
  const [password, setPassword] = useState("recoverai123");

  // Register fields
  const [regName, setRegName] = useState("");
  const [regMerchant, setRegMerchant] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regConfirm, setRegConfirm] = useState("");

  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Backend settings & diagnostics
  const [showConfig, setShowConfig] = useState(false);
  const [customUrl, setCustomUrl] = useState("");
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [checkingHealth, setCheckingHealth] = useState(false);

  useEffect(() => {
    setCustomUrl(getCustomBackendUrl() || "");
  }, []);

  async function checkBackend(target?: string) {
    setCheckingHealth(true);
    setHealthStatus(null);
    const res = await api.checkHealth(target);
    setHealthOk(res.ok);
    setHealthStatus(res.message);
    setCheckingHealth(false);
  }

  function handleSaveBackendUrl(e: React.FormEvent) {
    e.preventDefault();
    setCustomBackendUrl(customUrl);
    checkBackend(customUrl);
  }

  function handleResetBackendUrl() {
    setCustomBackendUrl(null);
    setCustomUrl("");
    checkBackend("");
  }

  function parseErrorMessage(e: any): string {
    if (e instanceof ApiError) {
      if (e.status === 401) {
        return e.message || "Invalid credentials. Please check your email and password.";
      }
      if (e.status === 429) {
        return "Rate limit exceeded. Please wait a moment before trying again.";
      }
      if (e.status === 502 || e.status === 500) {
        return `Backend connection error (${e.status}). The frontend cannot reach the API service. Verify your backend URL in settings below.`;
      }
      if (e.status === 0) {
        return `${e.message}`;
      }
      return `${e.message} (HTTP ${e.status})`;
    }
    return String(e?.message || "An unexpected error occurred");
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await api.post<{ access_token: string }>("/auth/login", { email, password });
      setToken(r.access_token);
      router.replace("/dashboard");
    } catch (e: any) {
      setErr(parseErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (regPassword !== regConfirm) {
      setErr("Passwords do not match");
      return;
    }
    if (regPassword.length < 8) {
      setErr("Password must be at least 8 characters");
      return;
    }
    setBusy(true);
    try {
      const r = await api.post<{ access_token: string }>("/auth/register", {
        email: regEmail,
        password: regPassword,
        full_name: regName,
        merchant_name: regMerchant || regName + "'s Store",
        role: "admin",
      });
      setToken(r.access_token);
      router.replace("/dashboard");
    } catch (e: any) {
      setErr(parseErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const effectiveApi = getEffectiveApiBase() || "(Proxied via Next.js rewrites)";

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm space-y-4">
        {/* Logo */}
        <div className="flex items-center gap-2 justify-center mb-6">
          <ShieldCheck className="h-6 w-6 text-accent2" />
          <span className="text-xl font-semibold tracking-tight">RECOVERAI</span>
        </div>

        {/* Tab toggle */}
        <div className="flex rounded-lg overflow-hidden mb-4 border border-white/10">
          <button
            onClick={() => { setMode("login"); setErr(null); }}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${
              mode === "login" ? "bg-accent text-white" : "bg-transparent text-muted hover:text-white"
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setMode("register"); setErr(null); }}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${
              mode === "register" ? "bg-accent text-white" : "bg-transparent text-muted hover:text-white"
            }`}
          >
            Register
          </button>
        </div>

        {/* Login Form */}
        {mode === "login" && (
          <form onSubmit={handleLogin} className="card space-y-4">
            <div>
              <div className="text-sm font-medium mb-1">Email</div>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <div className="text-sm font-medium mb-1">Password</div>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {err && (
              <div className="text-xs text-danger bg-danger/10 border border-danger/20 rounded p-2.5 space-y-1">
                <div className="font-semibold flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>Authentication Notice</span>
                </div>
                <div>{err}</div>
              </div>
            )}
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
            <div className="text-xs text-muted text-center">
              Demo: demo@recoverai.dev / recoverai123
            </div>
          </form>
        )}

        {/* Register Form */}
        {mode === "register" && (
          <form onSubmit={handleRegister} className="card space-y-4">
            <div>
              <div className="text-sm font-medium mb-1">Full Name</div>
              <input
                className="input"
                type="text"
                placeholder="Your name"
                value={regName}
                onChange={(e) => setRegName(e.target.value)}
                required
              />
            </div>
            <div>
              <div className="text-sm font-medium mb-1">Business / Merchant Name</div>
              <input
                className="input"
                type="text"
                placeholder="e.g. My Store"
                value={regMerchant}
                onChange={(e) => setRegMerchant(e.target.value)}
              />
            </div>
            <div>
              <div className="text-sm font-medium mb-1">Email</div>
              <input
                className="input"
                type="email"
                placeholder="you@example.com"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <div className="text-sm font-medium mb-1">Password</div>
              <input
                className="input"
                type="password"
                placeholder="Min. 8 characters"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                required
              />
            </div>
            <div>
              <div className="text-sm font-medium mb-1">Confirm Password</div>
              <input
                className="input"
                type="password"
                placeholder="Repeat password"
                value={regConfirm}
                onChange={(e) => setRegConfirm(e.target.value)}
                required
              />
            </div>
            {err && (
              <div className="text-xs text-danger bg-danger/10 border border-danger/20 rounded p-2.5">
                {err}
              </div>
            )}
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? "Creating account…" : "Create Account"}
            </button>
            <div className="text-xs text-muted text-center">
              A new merchant workspace will be created for you.
            </div>
          </form>
        )}

        {/* Backend Configuration & Connectivity Helper */}
        <div className="pt-2">
          <button
            type="button"
            onClick={() => setShowConfig(!showConfig)}
            className="w-full flex items-center justify-center gap-1.5 text-xs text-muted hover:text-white transition-colors py-1"
          >
            <Settings className="h-3.5 w-3.5" />
            <span>{showConfig ? "Hide API Configuration" : "API Connection Settings"}</span>
          </button>

          {showConfig && (
            <div className="mt-3 p-3 rounded-lg bg-panel border border-border space-y-3 text-xs">
              <div>
                <div className="text-muted text-[11px] mb-1">Current Active Backend:</div>
                <div className="font-mono text-accent2 bg-panel2 px-2 py-1 rounded break-all">
                  {effectiveApi}
                </div>
              </div>

              <form onSubmit={handleSaveBackendUrl} className="space-y-2">
                <div className="text-muted text-[11px]">Override Backend URL (Optional):</div>
                <input
                  type="text"
                  placeholder="https://recoverai-backend.onrender.com"
                  value={customUrl}
                  onChange={(e) => setCustomUrl(e.target.value)}
                  className="input text-xs py-1 px-2 font-mono"
                />
                <div className="flex gap-2">
                  <button type="submit" className="btn-primary text-xs py-1 px-2.5 flex-1">
                    Apply URL
                  </button>
                  <button
                    type="button"
                    onClick={handleResetBackendUrl}
                    className="btn-ghost text-xs py-1 px-2 text-muted hover:text-white"
                  >
                    Reset
                  </button>
                </div>
              </form>

              <div className="pt-2 border-t border-border flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => checkBackend(customUrl)}
                  disabled={checkingHealth}
                  className="btn-ghost text-xs py-1 px-2 flex items-center gap-1.5"
                >
                  <RefreshCw className={`h-3 w-3 ${checkingHealth ? "animate-spin" : ""}`} />
                  <span>Test Connection</span>
                </button>
                {healthStatus && (
                  <div className={`flex items-center gap-1 text-[11px] ${healthOk ? "text-ok" : "text-danger"}`}>
                    {healthOk ? <CheckCircle2 className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                    <span>{healthOk ? "Connected" : "Unreachable"}</span>
                  </div>
                )}
              </div>

              {healthStatus && (
                <div className="text-[10px] text-muted font-mono break-all bg-panel2 p-1.5 rounded">
                  {healthStatus}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

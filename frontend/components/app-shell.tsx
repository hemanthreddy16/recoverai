"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  Receipt,
  Bot,
  Sparkles,
  LineChart,
  Server,
  FlaskConical,
  ScrollText,
  Settings,
  ShieldCheck,
  LogOut,
  Zap,
} from "lucide-react";
import { getToken, clearToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/cases", label: "Cases", icon: FolderKanban },
  { href: "/bills", label: "Bills & EMIs", icon: Receipt, badge: "NEW" },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/command", label: "AI Command Center", icon: Sparkles, badge: "AI" },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/mcp", label: "MCP", icon: Server },
  { href: "/demo", label: "Demo Center", icon: FlaskConical },
  { href: "/audit", label: "Audit Log", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (pathname === "/login") {
      setReady(true);
      return;
    }
    if (!getToken()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [pathname, router]);

  function logout() {
    clearToken();
    router.replace("/login");
  }

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center text-muted">
        <span className="animate-pulse2">Loading RECOVERAI Command Center…</span>
      </div>
    );
  }

  if (pathname === "/login") {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      <aside className="w-64 shrink-0 border-r border-border bg-panel flex flex-col justify-between">
        <div>
          {/* Brand header */}
          <div className="px-5 py-4 border-b border-border">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center text-accent2 shadow-sm">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="font-bold tracking-tight text-white flex items-center gap-1.5 text-base">
                  RECOVERAI
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-accent2/20 text-accent2 font-mono font-medium">V2</span>
                </div>
                <div className="text-[11px] text-muted font-medium">Autonomous Revenue Ops</div>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            <div className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted/70">
              Platform Command
            </div>
            {NAV.map((n) => {
              const active = pathname === n.href || (n.href !== "/dashboard" && pathname.startsWith(n.href));
              const Icon = n.icon;
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  className={`sidebar-link flex items-center justify-between text-sm ${
                    active ? "sidebar-link-active font-semibold" : "text-muted hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`h-4 w-4 ${active ? "text-accent2" : "text-muted"}`} />
                    <span>{n.label}</span>
                  </div>
                  {n.badge && (
                    <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-accent/30 text-accent2 border border-accent/50">
                      {n.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Footer info & Logout */}
        <div className="p-3 border-t border-border space-y-2">
          <div className="px-3 py-2 rounded-lg bg-panel2 border border-border/80 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-ok animate-pulse2" />
              <span className="text-muted text-[11px]">8 Agents Active</span>
            </div>
            <span className="text-[11px] text-accent2 font-mono">MCP Gateway</span>
          </div>

          <button onClick={logout} className="sidebar-link w-full text-muted hover:text-danger text-sm flex items-center gap-2 px-3 py-2 rounded-md hover:bg-panel2 transition-colors">
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto bg-bg">
        <div className="mx-auto max-w-7xl px-6 py-6">{children}</div>
      </main>
    </div>
  );
}

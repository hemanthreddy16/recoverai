import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "RESURGE — Autonomous Revenue Intelligence",
  description: "Predict. Recover. Learn. — Real-time revenue intelligence with multi-agent recovery, ML prediction & MCP remediation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { Toaster } from "sonner";

import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";

export const metadata: Metadata = {
  title: "job-agent-arkode web",
  description: "Painel operacional do agente de vagas",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 p-6">{children}</main>
        </div>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}

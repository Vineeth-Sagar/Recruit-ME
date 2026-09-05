import type { Metadata } from "next";

import { AuthProvider } from "@/lib/auth";
import { QueryProvider } from "@/lib/query";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Recruit-ME",
  description: "Multi-tenant job-search automation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
        <Toaster richColors position="top-center" />
      </body>
    </html>
  );
}

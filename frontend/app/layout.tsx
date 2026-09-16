import type { Metadata } from "next";

import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "MultiSource AI — Secure Research Intelligence", template: "%s · MultiSource AI" },
  description: "Understand private documents, websites, and the live web with secure, evidence-backed AI research."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><body><Providers>{children}</Providers></body></html>;
}

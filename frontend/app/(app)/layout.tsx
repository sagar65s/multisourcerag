import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";

export default function ApplicationLayout({ children }: { children: React.ReactNode }) { return <AuthGuard><AppShell>{children}</AppShell></AuthGuard>; }

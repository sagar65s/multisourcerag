import { apiFetch } from "@/services/api";

export type ProviderStatus = {
  name: string;
  model?: string;
  priority?: number;
  enabled: boolean;
  health: string;
  requests?: number;
  errors?: number;
  rate_limits?: number;
  average_latency_ms?: number;
  daily_requests?: number;
  daily_quota?: number;
  rpm?: number;
  cooldown_until?: string | null;
};
export type AdminOverview = {
  metrics: Record<string, number>;
  system: Record<string, string>;
  operations: {
    started_at: string;
    uptime_seconds: number;
    active_requests: number;
    total_requests: number;
    server_errors: number;
    average_duration_ms: number;
    routes: Array<{
      method: string;
      route: string;
      requests: number;
      errors: number;
      average_duration_ms: number;
    }>;
  };
  providers: { llm: ProviderStatus[]; search: ProviderStatus[] };
  activity: Array<{
    date: string;
    conversations: number;
    documents: number;
    research: number;
    websites: number;
  }>;
  audit_logs: Array<{
    action: string;
    status: string;
    resource_type?: string;
    actor: string;
    created_at: string;
  }>;
  security_logs: Array<{ event: string; severity: string; created_at: string }>;
};
export const getAdminOverview = () =>
  apiFetch<AdminOverview>("/admin/overview");

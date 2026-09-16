import { apiFetch } from "@/services/api";
export type DashboardOverview = {
  metrics: {
    workspaces: number;
    documents: number;
    websites: number;
    conversations: number;
    saved_answers: number;
    active_jobs: number;
    indexed_sources: number;
  };
  workspaces: Array<{
    id: string;
    name: string;
    description: string;
    document_count: number;
    website_count: number;
    updated_at: string;
  }>;
  conversations: Array<{
    id: string;
    title: string;
    workspace_id: string | null;
    message_count: number;
    last_message_preview: string;
    updated_at: string;
  }>;
  processing_jobs: Array<{
    id: string;
    source_name?: string;
    kind?: string;
    status: string;
    stage?: string;
    attempt?: number;
    error_code?: string | null;
    can_cancel: boolean;
    can_retry: boolean;
    updated_at: string;
  }>;
};
export const getDashboardOverview = () =>
  apiFetch<DashboardOverview>("/dashboard");

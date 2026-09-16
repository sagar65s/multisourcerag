import { apiFetch } from "@/services/api";

export type Job = {
  id: string;
  workspace_id: string | null;
  source_id: string;
  source_name: string;
  kind: string;
  status: "queued" | "processing" | "cancel_requested" | "canceled" | "completed" | "failed";
  stage: string;
  attempt: number;
  error_code: string | null;
  can_cancel: boolean;
  can_retry: boolean;
  created_at: string;
  updated_at: string;
};

export const listJobs = () => apiFetch<Job[]>("/jobs");
export const cancelJob = (id: string) => apiFetch<Job>(`/jobs/${id}/cancel`, { method: "POST" });
export const retryJob = (id: string) => apiFetch<Job>(`/jobs/${id}/retry`, { method: "POST" });

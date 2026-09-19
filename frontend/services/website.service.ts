import { apiFetch } from "@/services/api";

export type WebsiteStatus = "queued" | "extracting" | "chunking" | "embedding" | "indexing" | "completed" | "failed";
export type WebsiteSource = { id: string; workspace_id: string; url: string; domain: string; title: string | null; meta_description: string | null; content_preview: string | null; scope: "single" | "selected" | "full"; status: WebsiteStatus; indexed_pages: number; chunk_count: number; important_headings: string[]; internal_links: string[]; external_links: string[]; error_message: string | null; analysis_method: "direct" | "browser" | "github_api" | "search_fallback"; source_notice: string | null; created_at: string; updated_at: string };
export type WebsiteInput = { workspace_id: string; url: string; scope: "single" | "selected" | "full"; selected_urls: string[]; max_depth: number; max_pages: number };

export const listWebsites = (workspaceId?: string) => apiFetch<WebsiteSource[]>(`/websites${workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ""}`);
export const addWebsite = (payload: WebsiteInput) => apiFetch<WebsiteSource>("/websites", { method: "POST", body: JSON.stringify(payload) });
export const deleteWebsite = (id: string) => apiFetch<void>(`/websites/${id}`, { method: "DELETE" });
export const reindexWebsite = (id: string) => apiFetch<WebsiteSource>(`/websites/${id}/reindex`, { method: "POST" });

import { getAuthenticatedUser } from "@/lib/firebase";
import { apiFetch } from "@/services/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type ProcessingStatus = "queued" | "validating" | "security_check" | "extracting" | "ocr" | "cleaning" | "chunking" | "embedding" | "indexing" | "completed" | "failed";
export type DocumentItem = { id: string; workspace_id: string; original_name: string; media_type: string; size_bytes: number; page_count: number; chunk_count: number; ocr_used: boolean; status: ProcessingStatus; error_message: string | null; created_at: string; updated_at: string };
export type Workspace = { id: string; name: string; description: string; document_count: number; website_count: number; created_at: string; updated_at: string };

export const listWorkspaces = () => apiFetch<Workspace[]>("/workspaces");
export const createWorkspace = (name: string) => apiFetch<Workspace>("/workspaces", { method: "POST", body: JSON.stringify({ name, description: "Private research workspace" }) });
export const listDocuments = (workspaceId?: string) => apiFetch<DocumentItem[]>(`/documents${workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ""}`);
export const deleteDocument = (id: string) => apiFetch<void>(`/documents/${id}`, { method: "DELETE" });
export const reindexDocument = (id: string) => apiFetch<DocumentItem>(`/documents/${id}/reindex`, { method: "POST" });

export async function uploadDocuments(workspaceId: string, files: File[]): Promise<DocumentItem[]> {
  const token = await (await getAuthenticatedUser())?.getIdToken();
  if (!token) throw new Error("Please sign in before uploading private documents.");
  const form = new FormData();
  form.append("workspace_id", workspaceId);
  files.forEach((file) => form.append("files", file));
  const response = await fetch(`${API_URL}/documents/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error?.message ?? body?.detail ?? "Could not upload these documents.");
  return body.documents as DocumentItem[];
}

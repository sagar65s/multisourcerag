import { apiFetch } from "@/services/api";
export type Workspace = {
  id: string;
  name: string;
  description: string;
  document_count: number;
  website_count: number;
  created_at: string;
  updated_at: string;
};
export const listWorkspaces = () => apiFetch<Workspace[]>("/workspaces");
export const createWorkspace = (name: string, description = "") =>
  apiFetch<Workspace>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
export const renameWorkspace = (id: string, name: string) =>
  apiFetch<Workspace>(`/workspaces/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
export const deleteWorkspace = (id: string) =>
  apiFetch<void>(`/workspaces/${id}`, { method: "DELETE" });

import { apiFetch } from "@/services/api";
import type { Citation } from "@/components/citations/citation-drawer";

export type Conversation = {
  id: string;
  title: string;
  workspace_id: string | null;
  mode: "auto" | "general" | "knowledge" | "website" | "web" | "both";
  language: "English" | "Tamil" | "Hindi";
  message_count: number;
  last_message_preview: string;
  created_at: string;
  updated_at: string;
};
export type StoredMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources: Citation[];
  evidence_status:
    | "strongly_supported"
    | "supported"
    | "limited_evidence"
    | "no_evidence"
    | "conflicting_evidence"
    | "general_answer"
    | null;
  provider: string | null;
  created_at: string;
};
export const listConversations = (search = "") =>
  apiFetch<Conversation[]>(
    `/conversations${search ? `?search=${encodeURIComponent(search)}` : ""}`,
  );
export const getConversation = (id: string) =>
  apiFetch<Conversation>(`/conversations/${id}`);
export const listConversationMessages = (id: string) =>
  apiFetch<StoredMessage[]>(`/conversations/${id}/messages`);
export const renameConversation = (id: string, title: string) =>
  apiFetch<Conversation>(`/conversations/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
export const deleteConversation = (id: string) =>
  apiFetch<void>(`/conversations/${id}`, { method: "DELETE" });

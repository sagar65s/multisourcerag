import type { Citation } from "@/components/citations/citation-drawer";
import { apiFetch } from "@/services/api";

export type SavedAnswer = {
  id: string;
  conversation_id: string;
  message_id: string;
  workspace_id: string | null;
  question: string;
  answer: string;
  sources: Citation[];
  created_at: string;
};
export type Bookmark = {
  id: string;
  conversation_id: string;
  message_id: string;
  workspace_id: string | null;
  source: Citation;
  note: string;
  created_at: string;
};
export const saveAnswer = (messageId: string) =>
  apiFetch<SavedAnswer>("/saved", {
    method: "POST",
    body: JSON.stringify({ message_id: messageId }),
  });
export const listSavedAnswers = () => apiFetch<SavedAnswer[]>("/saved");
export const deleteSavedAnswer = (id: string) =>
  apiFetch<void>(`/saved/${id}`, { method: "DELETE" });
export const saveBookmark = (messageId: string, sourceId: string, note = "") =>
  apiFetch<Bookmark>("/bookmarks", {
    method: "POST",
    body: JSON.stringify({ message_id: messageId, source_id: sourceId, note }),
  });
export const listBookmarks = () => apiFetch<Bookmark[]>("/bookmarks");
export const deleteBookmark = (id: string) =>
  apiFetch<void>(`/bookmarks/${id}`, { method: "DELETE" });
export const sendFeedback = (
  messageId: string,
  helpful: boolean,
  reasons: string[] = [],
) =>
  apiFetch<void>(`/messages/${messageId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ helpful, reasons }),
  });

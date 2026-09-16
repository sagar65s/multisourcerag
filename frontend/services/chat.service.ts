import { getAuthenticatedUser } from "@/lib/firebase";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export type ChatStreamEvent = { event: string; data: Record<string, unknown> };

export async function streamChat(
  query: string,
  workspaceId: string,
  mode: "auto" | "general" | "knowledge" | "website" | "web" | "both",
  language: "English" | "Tamil" | "Hindi",
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
  conversationId?: string | null,
  documentIds: string[] = [],
  websiteIds: string[] = [],
): Promise<void> {
  const token = await (await getAuthenticatedUser())?.getIdToken();
  if (!token) throw new Error("Please sign in before starting a private chat.");
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      query,
      mode,
      workspace_id: workspaceId || null,
      language,
      conversation_id: conversationId || null,
      document_ids: documentIds.length ? documentIds : null,
      website_ids: websiteIds.length ? websiteIds : null,
    }),
    signal,
  });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ??
        body?.detail ??
        "The chat service is unavailable.",
    );
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;
  let failure = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const event = block
        .split("\n")
        .find((line) => line.startsWith("event:"))
        ?.slice(6)
        .trim();
      const dataLine = block
        .split("\n")
        .find((line) => line.startsWith("data:"))
        ?.slice(5)
        .trim();
      if (event && dataLine) {
        const data = JSON.parse(dataLine) as Record<string, unknown>;
        onEvent({ event, data });
        if (event === "complete") finished = true;
        if (event === "error") failure = String(data.message ?? "Chat could not complete.");
      }
    }
    if (done) break;
  }
  if (!signal?.aborted && !finished) {
    throw new Error(failure || "The answer stopped early. Please try again.");
  }
}

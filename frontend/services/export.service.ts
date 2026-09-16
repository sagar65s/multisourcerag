import { getAuthenticatedUser } from "@/lib/firebase";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export type ExportSource =
  | "conversation"
  | "research"
  | "intelligence"
  | "saved_answer";
export type ExportFormat = "pdf" | "docx" | "markdown" | "txt";
export async function downloadExport(
  sourceType: ExportSource,
  sourceId: string,
  format: ExportFormat,
) {
  const token = await (await getAuthenticatedUser())?.getIdToken();
  if (!token) throw new Error("Please sign in before exporting private data.");
  const response = await fetch(`${API_URL}/exports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      source_type: sourceType,
      source_id: sourceId,
      format,
      include_citations: true,
    }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ?? body?.detail ?? "Could not export this item.",
    );
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const name =
    disposition.match(/filename="([^"]+)"/)?.[1] ??
    `multisource-ai-export.${format === "markdown" ? "md" : format}`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

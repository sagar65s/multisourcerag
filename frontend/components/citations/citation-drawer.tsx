"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { BookOpenCheck, ExternalLink, FileText, Globe2, X } from "lucide-react";

import { Button } from "@/components/ui/button";

export type Citation = { id: string; source_type: "document" | "website" | "web"; document_id?: string; document_name?: string; title?: string; page_number?: number; heading?: string | null; passage: string; url?: string | null; date?: string | null; authority?: number };

export function CitationDrawer({ citation, onClose }: { citation: Citation | null; onClose: () => void }) {
  const isWeb = citation?.source_type === "web" || citation?.source_type === "website";
  return <Dialog.Root open={Boolean(citation)} onOpenChange={(open) => { if (!open) onClose(); }}><Dialog.Portal><Dialog.Overlay className="citation-overlay" /><Dialog.Content className="citation-drawer"><div className="citation-drawer-head"><div className="citation-icon">{isWeb ? <Globe2 size={20} /> : <FileText size={20} />}</div><div><span>{citation?.source_type === "web" ? "LIVE WEB EVIDENCE" : "AUTHORIZED EVIDENCE"}</span><Dialog.Title>{citation?.document_name ?? citation?.title ?? "Source"}</Dialog.Title><Dialog.Description>{citation?.source_type === "document" ? `Page ${citation.page_number}${citation.heading ? ` · ${citation.heading}` : ""}` : citation?.date ? `Published or updated ${citation.date}` : "Source date not provided"}</Dialog.Description></div><Dialog.Close asChild><Button variant="ghost" size="icon" aria-label="Close citation"><X size={18} /></Button></Dialog.Close></div><div className="evidence-passage"><BookOpenCheck size={17} /><blockquote>{citation?.passage}</blockquote></div>{citation?.url && <a className="open-source-link" href={citation.url} target="_blank" rel="noreferrer">Open original source <ExternalLink size={15} /></a>}<div className="citation-foot"><span className="triangle-badge">△ {citation?.id}</span><span>{citation?.source_type === "document" ? "Retrieved from your private workspace" : citation?.source_type === "website" ? "Retrieved from an indexed website" : "Retrieved from current web research"}</span></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}

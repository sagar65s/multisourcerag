"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Citation } from "@/components/citations/citation-drawer";

function citationLinks(content: string) { return content.replace(/\[(S\d+)](?!\()/g, "[$1](citation:$1)"); }

function safeMarkdownUrl(url: string) {
  if (/^citation:S\d+$/.test(url)) return url;
  try {
    const parsed = new URL(url);
    return ["https:", "http:", "mailto:"].includes(parsed.protocol) ? url : "";
  } catch {
    return "";
  }
}

export function AssistantMessage({ content, sources, onCitation }: { content: string; sources: Citation[]; onCitation: (source: Citation) => void }) {
  return <div className="assistant-content"><ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={safeMarkdownUrl} components={{ a: ({ href, children }) => { const id = href?.startsWith("citation:") ? href.slice(9) : null; const source = sources.find((item) => item.id === id); return source ? <button className="inline-citation" onClick={() => onCitation(source)}>{children}</button> : href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span>; } }}>{citationLinks(content || "…")}</ReactMarkdown>{sources.length > 0 && <div className="message-sources">{sources.map((source) => <button key={source.id} onClick={() => onCitation(source)}><span>△ {source.id}</span><div><strong>{source.document_name ?? source.title ?? "Source"}</strong><small>{source.source_type === "document" ? `Page ${source.page_number}${source.heading ? ` · ${source.heading}` : ""}` : source.date ?? source.url ?? "Website evidence"}</small></div></button>)}</div>}</div>;
}

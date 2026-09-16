"use client";

import { useState } from "react";
import { AssistantMessage } from "@/components/chat/assistant-message";
import { CitationDrawer, type Citation } from "@/components/citations/citation-drawer";

function normalizeResearchMarkdown(markdown: string) {
  const value = markdown.trim().replace(/\r\n/g, "\n");
  const fenced = value.match(/^```(?:markdown|md)?\s*\n([\s\S]*?)\n```\s*$/i);
  return (fenced?.[1] ?? value).replace(/\\([*#_>`~-])/g, "$1").trim();
}

export function ReportView({
  markdown,
  sources,
}: {
  markdown: string;
  sources: Citation[];
}) {
  const [active, setActive] = useState<Citation | null>(null);
  return (
    <>
      <article className="research-report">
        <AssistantMessage
          content={normalizeResearchMarkdown(markdown)}
          sources={sources}
          onCitation={setActive}
        />
      </article>
      <CitationDrawer citation={active} onClose={() => setActive(null)} />
    </>
  );
}

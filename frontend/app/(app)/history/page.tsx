"use client";

import {
  Download,
  FileSearch,
  MessageSquareText,
  Pencil,
  Search,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Reveal } from "@/components/animations/reveal";
import { Button } from "@/components/ui/button";
import {
  deleteConversation,
  listConversations,
  renameConversation,
  type Conversation,
} from "@/services/conversation.service";
import { downloadExport, type ExportFormat } from "@/services/export.service";
import {
  listResearch,
  type ResearchSession,
} from "@/services/research.service";

export default function HistoryPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [research, setResearch] = useState<ResearchSession[]>([]);
  const [tab, setTab] = useState<"chats" | "research">("chats");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [format, setFormat] = useState<ExportFormat>("pdf");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  useEffect(() => {
    const initialQuery = new URLSearchParams(window.location.search).get("q");
    if (initialQuery) setQuery(initialQuery);
    void (async () => {
      try {
        const [c, r] = await Promise.all([listConversations(), listResearch()]);
        setConversations(c);
        setResearch(r);
      } catch (reason) {
        setError(
          reason instanceof Error ? reason.message : "Could not load history.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  const chats = useMemo(
    () =>
      conversations.filter((item) =>
        `${item.title} ${item.last_message_preview}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [conversations, query],
  );
  const reports = useMemo(
    () =>
      research.filter((item) =>
        item.title.toLowerCase().includes(query.toLowerCase()),
      ),
    [research, query],
  );
  const saveRename = async (item: Conversation) => {
    const title = editTitle.trim();
    if (!title || title === item.title) {
      setEditingId(null);
      return;
    }
    try {
      const updated = await renameConversation(item.id, title);
      setConversations((items) =>
        items.map((value) => (value.id === item.id ? updated : value)),
      );
      setEditingId(null);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not rename conversation.",
      );
    }
  };
  return (
    <div className="history-page">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">PRIVATE ACTIVITY</span>
            <h1>History</h1>
            <p>
              Search, continue, rename, export, or remove your conversations and
              research reports.
            </p>
          </div>
          <div className="saved-format">
            <span>Export as</span>
            <select
              value={format}
              onChange={(event) =>
                setFormat(event.target.value as ExportFormat)
              }
            >
              <option value="pdf">PDF</option>
              <option value="docx">DOCX</option>
              <option value="markdown">Markdown</option>
              <option value="txt">TXT</option>
            </select>
          </div>
        </header>
      </Reveal>
      {error && (
        <div className="chat-error" role="alert">
          {error}
        </div>
      )}
      <section className="history-shell">
        <div className="saved-toolbar">
          <div className="saved-tabs">
            <button
              className={tab === "chats" ? "active" : ""}
              onClick={() => setTab("chats")}
              aria-pressed={tab === "chats"}
            >
              <MessageSquareText size={15} /> Conversations{" "}
              <span>{conversations.length}</span>
            </button>
            <button
              className={tab === "research" ? "active" : ""}
              onClick={() => setTab("research")}
              aria-pressed={tab === "research"}
            >
              <FileSearch size={15} /> Research <span>{research.length}</span>
            </button>
          </div>
          <label>
            <Search size={15} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search titles and recent messages"
              aria-label="Search history"
            />
          </label>
        </div>
        {loading ? (
          <div className="history-list-skeleton">Loading private history…</div>
        ) : tab === "chats" ? (
          <div className="conversation-grid">
            {chats.length === 0 ? (
              <HistoryEmpty />
            ) : (
              chats.map((item) => (
                <article key={item.id}>
                  <div className="conversation-mark">△</div>
                  <div>
                    <span>
                      {item.mode.replace("_", " ")} · {item.language}
                    </span>
                    {editingId === item.id ? (
                      <input
                        className="history-rename"
                        autoFocus
                        value={editTitle}
                        onChange={(event) => setEditTitle(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") void saveRename(item);
                          if (event.key === "Escape") setEditingId(null);
                        }}
                        aria-label="Conversation title"
                      />
                    ) : (
                      <h2>{item.title}</h2>
                    )}
                    <p>{item.last_message_preview || "Conversation created"}</p>
                    <small>
                      {item.message_count} messages ·{" "}
                      {new Date(item.updated_at).toLocaleString()}
                    </small>
                  </div>
                  <div>
                    <Link href={`/chat?conversation=${item.id}`}>Continue</Link>
                    <button
                      onClick={() => {
                        if (editingId === item.id) void saveRename(item);
                        else {
                          setEditingId(item.id);
                          setEditTitle(item.title);
                        }
                      }}
                      aria-label={
                        editingId === item.id
                          ? "Save conversation title"
                          : "Rename conversation"
                      }
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() =>
                        void downloadExport(
                          "conversation",
                          item.id,
                          format,
                        ).catch((reason) => setError(reason.message))
                      }
                      aria-label="Export conversation"
                    >
                      <Download size={14} />
                    </button>
                    <button
                      onClick={() =>
                        void deleteConversation(item.id)
                          .then(() =>
                            setConversations((items) =>
                              items.filter((value) => value.id !== item.id),
                            ),
                          )
                          .catch((reason) => setError(reason.message))
                      }
                      aria-label="Delete conversation"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        ) : (
          <div className="conversation-grid">
            {reports.length === 0 ? (
              <HistoryEmpty />
            ) : (
              reports.map((item) => (
                <article key={item.id}>
                  <div className="conversation-mark research">◇</div>
                  <div>
                    <span>
                      {item.kind.replaceAll("_", " ")} ·{" "}
                      {item.status.replaceAll("_", " ")}
                    </span>
                    <h2>{item.title}</h2>
                    <p>
                      {item.output_markdown?.slice(0, 180) ||
                        item.error_message ||
                        "Research is still processing."}
                    </p>
                    <small>
                      {item.source_count} sources ·{" "}
                      {new Date(item.updated_at).toLocaleString()}
                    </small>
                  </div>
                  <div>
                    <Link href={`/research?session=${item.id}`}>Open</Link>
                    {item.status === "completed" && (
                      <button
                        onClick={() =>
                          void downloadExport(
                            "research",
                            item.id,
                            format,
                          ).catch((reason) => setError(reason.message))
                        }
                        aria-label="Export research"
                      >
                        <Download size={14} />
                      </button>
                    )}
                  </div>
                </article>
              ))
            )}
          </div>
        )}
      </section>
    </div>
  );
}

function HistoryEmpty() {
  return (
    <div className="history-empty-state">
      <MessageSquareText size={28} />
      <strong>No matching history</strong>
      <p>
        Start a cited chat or deep research session to build your private
        history.
      </p>
      <Button asChild>
        <Link href="/chat">Start new chat</Link>
      </Button>
    </div>
  );
}

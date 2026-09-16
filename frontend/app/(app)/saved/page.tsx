"use client";

import {
  Archive,
  Bookmark,
  Download,
  FileText,
  Globe2,
  Search,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Reveal } from "@/components/animations/reveal";
import { AssistantMessage } from "@/components/chat/assistant-message";
import {
  CitationDrawer,
  type Citation,
} from "@/components/citations/citation-drawer";
import { Button } from "@/components/ui/button";
import { downloadExport, type ExportFormat } from "@/services/export.service";
import {
  deleteBookmark,
  deleteSavedAnswer,
  listBookmarks,
  listSavedAnswers,
  type Bookmark as BookmarkItem,
  type SavedAnswer,
} from "@/services/saved.service";

export default function SavedPage() {
  const [answers, setAnswers] = useState<SavedAnswer[]>([]);
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [tab, setTab] = useState<"answers" | "bookmarks">("answers");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [active, setActive] = useState<Citation | null>(null);
  const [format, setFormat] = useState<ExportFormat>("pdf");
  useEffect(() => {
    void (async () => {
      try {
        const [a, b] = await Promise.all([listSavedAnswers(), listBookmarks()]);
        setAnswers(a);
        setBookmarks(b);
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not load saved intelligence.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  const filteredAnswers = useMemo(
    () =>
      answers.filter((item) =>
        `${item.question} ${item.answer}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [answers, query],
  );
  const filteredBookmarks = useMemo(
    () =>
      bookmarks.filter((item) =>
        `${item.source.document_name ?? item.source.title ?? ""} ${item.note}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [bookmarks, query],
  );
  return (
    <div className="saved-page">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">PRIVATE COLLECTION</span>
            <h1>Saved intelligence</h1>
            <p>
              Answers and evidence bookmarks stay connected to their original
              authorized sources.
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
      <div className="saved-toolbar">
        <div className="saved-tabs">
          <button
            className={tab === "answers" ? "active" : ""}
            onClick={() => setTab("answers")}
          >
            <Archive size={15} /> Saved answers <span>{answers.length}</span>
          </button>
          <button
            className={tab === "bookmarks" ? "active" : ""}
            onClick={() => setTab("bookmarks")}
          >
            <Bookmark size={15} /> Evidence bookmarks{" "}
            <span>{bookmarks.length}</span>
          </button>
        </div>
        <label>
          <Search size={15} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search your private collection"
          />
        </label>
      </div>
      {loading ? (
        <div className="saved-skeletons">
          {[0, 1, 2].map((item) => (
            <span key={item} />
          ))}
        </div>
      ) : tab === "answers" ? (
        <div className="saved-answer-grid">
          {filteredAnswers.length === 0 ? (
            <Empty
              icon={<Archive size={28} />}
              title="No saved answers"
              text="Save a cited assistant response from Chat to keep it here."
            />
          ) : (
            filteredAnswers.map((item) => (
              <Reveal key={item.id}>
                <article className="saved-answer-card">
                  <header>
                    <div>
                      <span>SAVED ANSWER</span>
                      <time>
                        {new Date(item.created_at).toLocaleDateString()}
                      </time>
                    </div>
                    <h2>{item.question}</h2>
                  </header>
                  <div className="saved-answer-content">
                    <AssistantMessage
                      content={item.answer}
                      sources={item.sources}
                      onCitation={setActive}
                    />
                  </div>
                  <footer>
                    <div>
                      {item.sources.slice(0, 3).map((source) => (
                        <button
                          key={source.id}
                          onClick={() => setActive(source)}
                        >
                          △ {source.id}
                        </button>
                      ))}
                    </div>
                    <div>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Export saved answer"
                        onClick={() =>
                          void downloadExport(
                            "saved_answer",
                            item.id,
                            format,
                          ).catch((reason) => setError(reason.message))
                        }
                      >
                        <Download size={15} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Delete saved answer"
                        onClick={() =>
                          void deleteSavedAnswer(item.id)
                            .then(() =>
                              setAnswers((items) =>
                                items.filter((value) => value.id !== item.id),
                              ),
                            )
                            .catch((reason) => setError(reason.message))
                        }
                      >
                        <Trash2 size={15} />
                      </Button>
                    </div>
                  </footer>
                </article>
              </Reveal>
            ))
          )}
        </div>
      ) : (
        <div className="bookmark-grid">
          {filteredBookmarks.length === 0 ? (
            <Empty
              icon={<Bookmark size={28} />}
              title="No evidence bookmarks"
              text="Bookmark a citation from a persisted chat answer."
            />
          ) : (
            filteredBookmarks.map((item) => (
              <Reveal key={item.id}>
                <article className="bookmark-card">
                  <div className="bookmark-source-icon">
                    {item.source.source_type === "document" ? (
                      <FileText size={20} />
                    ) : (
                      <Globe2 size={20} />
                    )}
                  </div>
                  <div>
                    <span>
                      △ {item.source.id} · {item.source.source_type}
                    </span>
                    <h2>
                      {item.source.document_name ??
                        item.source.title ??
                        "Evidence source"}
                    </h2>
                    <p>{item.source.passage}</p>
                    <small>
                      {item.source.source_type === "document"
                        ? `Page ${item.source.page_number}${item.source.heading ? ` · ${item.source.heading}` : ""}`
                        : item.source.url}
                    </small>
                  </div>
                  <div>
                    <button
                      onClick={() => setActive(item.source)}
                      aria-label="Open evidence"
                    >
                      Open
                    </button>
                    <button
                      onClick={() =>
                        void deleteBookmark(item.id)
                          .then(() =>
                            setBookmarks((items) =>
                              items.filter((value) => value.id !== item.id),
                            ),
                          )
                          .catch((reason) => setError(reason.message))
                      }
                      aria-label="Delete bookmark"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </article>
              </Reveal>
            ))
          )}
        </div>
      )}
      <CitationDrawer citation={active} onClose={() => setActive(null)} />
    </div>
  );
}

function Empty({
  icon,
  title,
  text,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="saved-empty">
      <div>
        {icon}
        <span>△</span>
      </div>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

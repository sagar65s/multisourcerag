"use client";

import {
  AlertTriangle,
  BookOpenCheck,
  Clock3,
  Download,
  FlaskConical,
  Globe2,
  LoaderCircle,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Reveal } from "@/components/animations/reveal";
import { ReportView } from "@/components/research/report-view";
import { ResearchProgress } from "@/components/research/research-progress";
import { Button } from "@/components/ui/button";
import { listWorkspaces, type Workspace } from "@/services/document.service";
import { downloadExport } from "@/services/export.service";
import {
  deleteResearch,
  getResearch,
  listResearch,
  startResearch,
  type ResearchSession,
} from "@/services/research.service";

export default function ResearchPage() {
  const [question, setQuestion] = useState("");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [includePrivate, setIncludePrivate] = useState(true);
  const [includeWeb, setIncludeWeb] = useState(true);
  const [maxQueries, setMaxQueries] = useState(3);
  const [language, setLanguage] = useState<"English" | "Tamil" | "Hindi">(
    "English",
  );
  const [active, setActive] = useState<ResearchSession | null>(null);
  const [history, setHistory] = useState<ResearchSession[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    void Promise.all([listWorkspaces(), listResearch("deep_research")])
      .then(([spaces, sessions]) => {
        setWorkspaces(spaces);
        setWorkspaceId(spaces[0]?.id ?? "");
        if (!spaces.length) setIncludePrivate(false);
        setHistory(sessions);
      })
      .catch((reason) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not load research workspace.",
        ),
      );
  }, []);
  useEffect(() => {
    if (!active || ["completed", "failed"].includes(active.status)) return;
    const timer = window.setInterval(
      () => {
        if (document.visibilityState !== "visible") return;
        void getResearch(active.id)
          .then((session) => {
            setActive(session);
            if (["completed", "failed"].includes(session.status))
              setHistory((items) => [
                session,
                ...items.filter((item) => item.id !== session.id),
              ]);
          })
          .catch(() => setError("Research status could not be refreshed. Your report is still saved; retry after reconnecting."));
      },
      5_000,
    );
    return () => window.clearInterval(timer);
  }, [active]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
      !question.trim() ||
      (!includePrivate && !includeWeb) ||
      (includePrivate && !workspaceId)
    )
      return;
    setBusy(true);
    setError("");
    try {
      const session = await startResearch({
        question: question.trim(),
        workspace_id: includePrivate ? workspaceId : null,
        include_private: includePrivate,
        include_web: includeWeb,
        max_queries: maxQueries,
        language,
      });
      setActive(session);
      setQuestion("");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Deep research could not start.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function remove(id: string) {
    try {
      await deleteResearch(id);
      setHistory((items) => items.filter((item) => item.id !== id));
      if (active?.id === id) setActive(null);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not delete research.",
      );
    }
  }
  return (
    <div className="research-page">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">DEEP RESEARCH</span>
            <h1>Investigate beyond the first answer</h1>
            <p>
              Plan, search, read, cross-check, synthesize and independently
              verify.
            </p>
          </div>
          <div className="privacy-state">
            <ShieldCheck size={15} />
            Evidence-first
          </div>
        </header>
      </Reveal>
      {error && (
        <div className="document-alert" role="alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss error">×</button>
        </div>
      )}
      <div className="research-layout">
        <Reveal>
          <form className="research-form" onSubmit={submit}>
            <div className="research-prompt-icon">
              <FlaskConical size={24} />
              <span />
              <span />
            </div>
            <label>
              Research question
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={5}
                placeholder="What should be investigated, compared, or verified?"
                required
                minLength={10}
              />
            </label>
            <div className="research-sources">
              <button
                type="button"
                className={includePrivate ? "active" : ""}
                onClick={() => setIncludePrivate((value) => !value)}
                disabled={!workspaces.length}
              >
                <BookOpenCheck size={17} />
                <div>
                  <strong>Private knowledge</strong>
                  <span>Documents and indexed websites</span>
                </div>
                <i>{includePrivate ? "✓" : ""}</i>
              </button>
              <button
                type="button"
                className={includeWeb ? "active" : ""}
                onClick={() => setIncludeWeb((value) => !value)}
              >
                <Globe2 size={17} />
                <div>
                  <strong>Current web</strong>
                  <span>Fresh multi-query evidence</span>
                </div>
                <i>{includeWeb ? "✓" : ""}</i>
              </button>
            </div>
            {includePrivate && (
              <label>
                Source collection
                <select
                  value={workspaceId}
                  onChange={(event) => setWorkspaceId(event.target.value)}
                >
                  <option value="">Select collection</option>
                  {workspaces.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <div className="research-options">
              <label>
                Search queries
                <select
                  value={maxQueries}
                  onChange={(event) =>
                    setMaxQueries(Number(event.target.value))
                  }
                >
                  <option value={2}>2 focused</option>
                  <option value={3}>3 balanced</option>
                  <option value={4}>4 extensive</option>
                  <option value={5}>5 maximum</option>
                </select>
              </label>
              <label>
                Report language
                <select
                  value={language}
                  onChange={(event) =>
                    setLanguage(event.target.value as typeof language)
                  }
                >
                  <option>English</option>
                  <option>Tamil</option>
                  <option>Hindi</option>
                </select>
              </label>
            </div>
            <Button
              size="lg"
              disabled={
                busy ||
                question.trim().length < 10 ||
                (!includePrivate && !includeWeb) ||
                (includePrivate && !workspaceId)
              }
            >
              {busy ? (
                <>
                  <LoaderCircle className="spin" size={17} />
                  Starting…
                </>
              ) : (
                <>
                  <Search size={17} />
                  Start deep research
                </>
              )}
            </Button>
          </form>
        </Reveal>
        <div className="research-main">
          {active ? (
            <Reveal>
              <section className="active-research">
                <div className="active-research-head">
                  <div>
                    <span>{active.kind.replaceAll("_", " ")}</span>
                    <h2>{active.title}</h2>
                  </div>
                  <div className={`processing-state ${active.status}`}>
                    {active.status.replaceAll("_", " ")}
                  </div>
                </div>
                {active.status === "completed" && (
                  <div className="research-export-bar">
                    <div>
                      <strong>Research report ready</strong>
                      <span>Download the complete report with citations.</span>
                    </div>
                    <Button
                      variant="secondary"
                      onClick={() =>
                        void downloadExport("research", active.id, "pdf").catch(
                          (reason: Error) => setError(reason.message),
                        )
                      }
                    >
                      <Download size={17} /> Download PDF
                    </Button>
                  </div>
                )}
                <ResearchProgress stage={active.status} />
                {active.queries.length > 0 && (
                  <div className="query-chips">
                    {active.queries.map((item) => (
                      <span key={item}>{item}</span>
                    ))}
                  </div>
                )}
                {active.source_count > 0 && (
                  <div className="research-stats">
                    <span>
                      <Globe2 size={14} />
                      {active.source_count} verified candidates
                    </span>
                    <span>
                      <AlertTriangle size={14} />
                      {active.conflicts.length} conflict candidates
                    </span>
                  </div>
                )}
                {active.status === "failed" && (
                  <div className="research-error">{active.error_message}</div>
                )}
                {active.status === "completed" && active.output_markdown && (
                  <ReportView
                    markdown={active.output_markdown}
                    sources={active.sources}
                  />
                )}
              </section>
            </Reveal>
          ) : (
            <section className="research-placeholder">
              <div>△</div>
              <h2>Ready for a deeper investigation</h2>
              <p>Your live progress and verified report will appear here.</p>
            </section>
          )}
          <section className="research-history">
            <div className="document-library-head">
              <div>
                <span>RESEARCH HISTORY</span>
                <h2>Completed and recent sessions</h2>
              </div>
              <Clock3 size={17} />
            </div>
            {history.length === 0 ? (
              <p className="history-empty">No research sessions yet.</p>
            ) : (
              <div>
                {history.map((item) => (
                  <div
                    className="history-row"
                    key={item.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`Open research: ${item.title}`}
                    onClick={() => setActive(item)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setActive(item);
                      }
                    }}
                  >
                    <div>
                      <strong>{item.title}</strong>
                      <span>
                        {new Date(item.updated_at).toLocaleDateString()} ·{" "}
                        {item.source_count} sources
                      </span>
                    </div>
                    <i className={item.status}>
                      {item.status.replaceAll("_", " ")}
                    </i>
                    <button
                      aria-label="Delete research"
                      onClick={(event) => {
                        event.stopPropagation();
                        void remove(item.id);
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

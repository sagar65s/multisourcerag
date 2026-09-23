"use client";

import {
  AlertTriangle,
  Check,
  ExternalLink,
  Globe2,
  Link2,
  LoaderCircle,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { Reveal } from "@/components/animations/reveal";
import { Button } from "@/components/ui/button";
import { listWorkspaces, type Workspace } from "@/services/document.service";
import {
  addWebsite,
  deleteWebsite,
  listWebsites,
  reindexWebsite,
  type WebsiteSource,
} from "@/services/website.service";

const active = new Set([
  "queued",
  "extracting",
  "chunking",
  "embedding",
  "indexing",
]);
const labels: Record<string, string> = {
  queued: "Queued",
  extracting: "Fetching and parsing",
  chunking: "Smart chunking",
  embedding: "Creating embeddings",
  indexing: "Secure indexing",
  completed: "Ready",
  failed: "Failed",
};

function normalizeWebsiteInput(value: string) {
  const compact = value.trim();
  if (!compact || compact.includes("://")) return compact;
  const looksLikeAddress = compact.includes(".") || compact.startsWith("localhost");
  return looksLikeAddress ? `https://${compact}` : compact;
}

export default function WebsitesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [items, setItems] = useState<WebsiteSource[]>([]);
  const [url, setUrl] = useState("");
  const [scope, setScope] = useState<"single" | "selected" | "full">("single");
  const [selectedUrls, setSelectedUrls] = useState("");
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxPages, setMaxPages] = useState(20);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refresh = useCallback(
    async (target = workspaceId) => {
      try {
        setItems(await listWebsites(target || undefined));
        setError("");
      } catch (reason) {
        setError(
          reason instanceof Error ? reason.message : "Could not load websites.",
        );
      }
    },
    [workspaceId],
  );
  useEffect(() => {
    void (async () => {
      try {
        const spaces = await listWorkspaces();
        setWorkspaces(spaces);
        const first = spaces[0]?.id ?? "";
        setWorkspaceId(first);
        if (first) setItems(await listWebsites(first));
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not load website intelligence.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  useEffect(() => {
    if (!items.some((item) => active.has(item.status))) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 5_000);
    return () => window.clearInterval(timer);
  }, [items, refresh]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!workspaceId || !url) return;
    setBusy(true);
    setError("");
    try {
      const item = await addWebsite({
        workspace_id: workspaceId,
        url: normalizeWebsiteInput(url),
        scope,
        selected_urls:
          scope === "selected"
            ? selectedUrls
                .split("\n")
                .map(normalizeWebsiteInput)
                .filter(Boolean)
            : [],
        max_depth: scope === "full" ? maxDepth : 0,
        max_pages: scope === "single" ? 1 : maxPages,
      });
      setItems((current) => [item, ...current]);
      setUrl("");
      setSelectedUrls("");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Website analysis could not start.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function remove(id: string) {
    try {
      await deleteWebsite(id);
      setItems((current) => current.filter((item) => item.id !== id));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not remove website.",
      );
    }
  }
  async function retry(id: string) {
    try {
      await reindexWebsite(id);
      await refresh();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not restart website processing.",
      );
    }
  }
  return (
    <div className="websites-page">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">WEBSITE INTELLIGENCE</span>
            <h1>Understand the web</h1>
            <p>
              Analyze one page, selected pages, or a bounded allowed website.
            </p>
          </div>
          <div className="workspace-picker">
            <select
              value={workspaceId}
              onChange={(event) => {
                setWorkspaceId(event.target.value);
                void refresh(event.target.value);
              }}
              aria-label="Website workspace"
            >
              <option value="">Select workspace</option>
              {workspaces.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
        </header>
      </Reveal>
      {error && (
        <div className="document-alert" role="alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button onClick={() => setError("")}>×</button>
        </div>
      )}
      <div className="website-layout">
        <Reveal>
          <form className="website-analyzer" onSubmit={submit}>
            <div className="url-field">
              <Globe2 size={19} />
              <input
                type="text"
                inputMode="url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                required
                placeholder="Website name, domain, or GitHub repository URL"
                aria-label="Website URL"
              />
            </div>
            <div
              className="crawl-scope"
              role="radiogroup"
              aria-label="Crawl scope"
            >
              {(["single", "selected", "full"] as const).map((value) => (
                <button
                  type="button"
                  role="radio"
                  aria-checked={scope === value}
                  className={scope === value ? "active" : ""}
                  onClick={() => setScope(value)}
                  key={value}
                >
                  <span>△</span>
                  {value === "single"
                    ? "Single page"
                    : value === "selected"
                      ? "Selected pages"
                      : "Full website"}
                </button>
              ))}
            </div>
            {scope === "selected" && (
              <label className="selected-pages">
                Selected page URLs
                <textarea
                  value={selectedUrls}
                  onChange={(event) => setSelectedUrls(event.target.value)}
                  rows={4}
                  placeholder={
                    "https://example.com/docs\nhttps://example.com/about"
                  }
                />
              </label>
            )}
            {scope === "full" && (
              <div className="crawl-limits">
                <label>
                  Maximum depth
                  <input
                    type="number"
                    min={0}
                    max={3}
                    value={maxDepth}
                    onChange={(event) =>
                      setMaxDepth(Number(event.target.value))
                    }
                  />
                </label>
                <label>
                  Maximum pages
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={maxPages}
                    onChange={(event) =>
                      setMaxPages(Number(event.target.value))
                    }
                  />
                </label>
              </div>
            )}
            <div className="crawl-security">
              <Check size={15} />
              <span>
                Public pages only · Render cold starts are retried · JavaScript
                fallback is optional · private networks stay blocked
              </span>
            </div>
            <Button size="lg" disabled={busy || !workspaceId || !url}>
              {busy ? (
                <>
                  <LoaderCircle className="spin" size={17} />
                  Validating…
                </>
              ) : (
                <>
                  <Search size={17} />
                  Find, analyze and index
                </>
              )}
            </Button>
          </form>
        </Reveal>
        <Reveal delay={0.06}>
          <section className="website-results">
            <div className="document-library-head">
              <div>
                <span>INDEXED WEBSITES</span>
                <h2>Workspace sources</h2>
              </div>
              <button onClick={() => void refresh()}>
                <RefreshCw size={16} />
              </button>
            </div>
            {loading ? (
              <div className="document-skeletons">
                <span />
                <span />
                <span />
              </div>
            ) : items.length === 0 ? (
              <div className="document-empty">
                <div>△</div>
                <strong>No website intelligence yet</strong>
                <p>Paste a public URL to securely analyze it.</p>
              </div>
            ) : (
              <div className="website-card-list">
                {items.map((item) => (
                  <article className="website-card" key={item.id}>
                    <div className="website-favicon">
                      <Globe2 size={20} />
                    </div>
                    <div className="website-main">
                      <span>{item.domain}</span>
                      <h3>{item.title || item.url}</h3>
                      {item.meta_description && <p>{item.meta_description}</p>}
                      <div className="website-meta">
                        {item.indexed_pages > 0 && (
                          <span>{item.indexed_pages} pages</span>
                        )}
                        {item.chunk_count > 0 && (
                          <span>{item.chunk_count} chunks</span>
                        )}
                        <span>{item.scope}</span>
                        {item.analysis_method === "search_fallback" && (
                          <span>public search</span>
                        )}
                        {item.analysis_method === "github_api" && (
                          <span>GitHub API</span>
                        )}
                      </div>
                      <div className={`processing-state ${item.status}`}>
                        <i>
                          {active.has(item.status) ? (
                            <LoaderCircle className="spin" size={12} />
                          ) : item.status === "completed" ? (
                            <Check size={12} />
                          ) : (
                            <AlertTriangle size={12} />
                          )}
                        </i>
                        {labels[item.status]}
                      </div>
                      {item.error_message && (
                        <small>{item.error_message}</small>
                      )}
                      {item.source_notice && (
                        <small className="website-source-notice">
                          {item.source_notice}
                        </small>
                      )}
                      {item.status === "completed" &&
                        item.important_headings.length > 0 && (
                          <div className="heading-chips">
                            {item.important_headings
                              .slice(0, 4)
                              .map((heading) => (
                                <span key={heading}>{heading}</span>
                              ))}
                          </div>
                        )}
                      {item.status === "completed" && item.content_preview && (
                        <div className="website-content-overview">
                          <strong>Content overview</strong>
                          <p>{item.content_preview}</p>
                        </div>
                      )}
                    </div>
                    <div className="website-actions">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        aria-label="Open original website"
                      >
                        <ExternalLink size={15} />
                      </a>
                      {item.status === "completed" && (
                        <Link href={`/chat?workspace=${workspaceId}&mode=website&website=${item.id}`} aria-label="Ask questions about this website" title="Ask this website in Chat">
                          <Link2 size={15} />
                        </Link>
                      )}
                      {item.status === "failed" && (
                        <button onClick={() => void retry(item.id)}>
                          <RefreshCw size={15} />
                        </button>
                      )}
                      <button onClick={() => void remove(item.id)}>
                        <Trash2 size={15} />
                      </button>
                    </div>
                    <span className="corner-triangle" />
                  </article>
                ))}
              </div>
            )}
          </section>
        </Reveal>
      </div>
    </div>
  );
}

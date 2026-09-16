"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  Archive,
  ArrowUpRight,
  BookOpen,
  FileStack,
  FolderPlus,
  Globe2,
  LoaderCircle,
  MessageSquareText,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Square,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { Reveal } from "@/components/animations/reveal";
import { Button } from "@/components/ui/button";
import { getAuthenticatedUser } from "@/lib/firebase";
import {
  type DashboardOverview,
  getDashboardOverview,
} from "@/services/dashboard.service";
import { cancelJob, retryJob } from "@/services/job.service";
import {
  createWorkspace,
  deleteWorkspace,
  renameWorkspace,
} from "@/services/workspace.service";

const actions = [
  [
    MessageSquareText,
    "Ask anything",
    "Start a source-grounded conversation",
    "/chat",
  ],
  [
    UploadCloud,
    "Upload knowledge",
    "PDF, DOCX, text, scans and images",
    "/documents",
  ],
  [
    Globe2,
    "Analyze a website",
    "Index one page or an allowed site",
    "/websites",
  ],
  [
    Search,
    "Deep research",
    "Cross-check fresh authoritative evidence",
    "/research",
  ],
] as const;
const metricIcons = {
  indexed_sources: BookOpen,
  conversations: MessageSquareText,
  saved_answers: Archive,
  active_jobs: LoaderCircle,
} as const;

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [displayName, setDisplayName] = useState("there");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [jobBusy, setJobBusy] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [renameTarget, setRenameTarget] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const load = () =>
    getDashboardOverview()
      .then((overview) => { setData(overview); setError(""); })
      .catch((reason: Error) => setError(reason.message));
  useEffect(() => {
    void load();
    const polling = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, 30_000);
    void getAuthenticatedUser().then((user) =>
      setDisplayName(
        user?.displayName?.split(" ")[0] ??
          user?.email?.split("@")[0] ??
          "there",
      ),
    );
    return () => window.clearInterval(polling);
  }, []);
  const ask = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim())
      router.push(`/chat?prompt=${encodeURIComponent(query.trim())}`);
  };
  const create = async () => {
    if (name.trim().length < 2) return;
    setBusy(true);
    try {
      await createWorkspace(name.trim(), "Private source collection");
      setName("");
      setCreateOpen(false);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not create workspace.",
      );
    } finally {
      setBusy(false);
    }
  };
  const rename = async () => {
    if (!renameTarget || renameTarget.name.trim().length < 2) return;
    setBusy(true);
    try {
      await renameWorkspace(renameTarget.id, renameTarget.name.trim());
      setRenameTarget(null);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not rename workspace.",
      );
    } finally {
      setBusy(false);
    }
  };
  const remove = async () => {
    if (!deleteTarget) return;
    setBusy(true);
    try {
      await deleteWorkspace(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not delete workspace.",
      );
    } finally {
      setBusy(false);
    }
  };
  const controlJob = async (id: string, action: "cancel" | "retry") => {
    setJobBusy(id);
    setError("");
    try {
      if (action === "cancel") await cancelJob(id);
      else await retryJob(id);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : `Could not ${action} this job.`);
    } finally {
      setJobBusy(null);
    }
  };
  return (
    <div className="dashboard">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">YOUR AI RESEARCH HOME</span>
            <h1>Welcome back, {displayName}.</h1>
            <p>What would you like to understand today?</p>
          </div>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus size={18} /> Create collection
          </Button>
        </header>
      </Reveal>
      {error && (
        <div className="document-alert" role="alert">
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss">
            <X size={15} />
          </button>
        </div>
      )}
      {data && data.workspaces.length === 0 && <section className="collection-guide" aria-label="Source collection guide">
        <div className="collection-guide-icon">
          <FolderPlus size={26} />
        </div>
        <div>
          <span>START HERE</span>
          <h2>Create a source collection</h2>
          <p>
            A collection keeps related documents, websites and chats together.
            Create one, add your sources, then ask questions from Chat.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Sparkles size={17} /> Create my collection
        </Button>
      </section>}
      <form className="quick-ask" onSubmit={ask}>
        <div className="ask-icon">
          <Sparkles size={21} />
        </div>
        <label>
          <span>QUICK ASK</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask across your private knowledge and the live web…"
            aria-label="Quick question"
          />
        </label>
        <Button size="icon" disabled={!query.trim()} aria-label="Ask">
          <ArrowUpRight size={19} />
        </Button>
      </form>
      <div className="action-grid">
        {actions.map(([Icon, title, text, href], index) => (
          <Reveal delay={index * 0.05} key={title}>
            <Link className="action-card" href={href}>
              <div className="action-icon">
                <Icon size={21} />
              </div>
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
              <ArrowUpRight className="action-arrow" size={18} />
              <span className="corner-triangle" />
            </Link>
          </Reveal>
        ))}
      </div>
      {!data ? (
        <div className="dashboard-live-skeleton">
          {Array.from({ length: 4 }).map((_, index) => (
            <i key={index} />
          ))}
        </div>
      ) : (
        <>
          <div className="dashboard-metrics">
            {Object.entries(metricIcons).map(([key, Icon]) => (
              <article key={key}>
                <Icon size={17} />
                <div>
                  <strong>
                    {data.metrics[key as keyof typeof data.metrics]}
                  </strong>
                  <span>{key.replaceAll("_", " ")}</span>
                </div>
              </article>
            ))}
          </div>
          <div className="dashboard-grid">
            <Reveal className="activity-panel">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <span>RECENT ACTIVITY</span>
                    <h2>Continue where you left off</h2>
                  </div>
                  <Link href="/history">View all</Link>
                </div>
                {data.conversations.length ? (
                  <div className="dashboard-recents">
                    {data.conversations.map((item) => (
                      <Link
                        href={`/chat?conversation=${item.id}`}
                        key={item.id}
                      >
                        <i>△</i>
                        <div>
                          <strong>{item.title}</strong>
                          <span>
                            {item.last_message_preview ||
                              `${item.message_count} messages`}
                          </span>
                        </div>
                        <time>
                          {new Date(item.updated_at).toLocaleDateString("en-GB")}
                        </time>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="empty-inline">
                    <div className="empty-mark">△</div>
                    <h3>Your research trail starts here</h3>
                    <p>
                      Ask a question or add a source. Conversations will appear
                      here.
                    </p>
                    <Button asChild variant="secondary" size="sm">
                      <Link href="/chat">Start a chat</Link>
                    </Button>
                  </div>
                )}
              </section>
            </Reveal>
            <Reveal className="workspace-panel" delay={0.08}>
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <span>SOURCE COLLECTIONS</span>
                    <h2>Your organized knowledge</h2>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setCreateOpen(true)}
                  >
                    <FolderPlus size={15} /> Add
                  </Button>
                </div>
                {data.workspaces.length ? (
                  <div className="workspace-list-live">
                    {data.workspaces.map((item) => (
                      <div className="workspace-preview" key={item.id}>
                        <div className="mini-pattern">
                          <span />
                          <span />
                          <span />
                        </div>
                        <Link href={`/documents?workspace=${item.id}`}>
                          <strong>{item.name}</strong>
                          <p>
                            <FileStack size={14} />
                            {item.document_count} documents ·{" "}
                            <Globe2 size={14} />
                            {item.website_count} websites
                          </p>
                        </Link>
                        <div className="workspace-actions">
                          <button
                            onClick={() =>
                              setRenameTarget({ id: item.id, name: item.name })
                            }
                            aria-label={`Rename ${item.name}`}
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() =>
                              setDeleteTarget({ id: item.id, name: item.name })
                            }
                            aria-label={`Delete ${item.name}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-inline compact">
                    <div className="empty-mark">△</div>
                    <h3>No collection yet</h3>
                    <p>Create one to organize documents and websites.</p>
                    <Button size="sm" onClick={() => setCreateOpen(true)}>
                      Create collection
                    </Button>
                  </div>
                )}
                <div className="usage-row">
                  <span>
                    <BookOpen size={16} /> Sources indexed
                  </span>
                  <strong>{data.metrics.indexed_sources}</strong>
                </div>
              </section>
            </Reveal>
          </div>
          {data.processing_jobs.length > 0 && (
            <Reveal>
              <section className="panel processing-strip">
                <div className="panel-heading">
                  <div>
                    <span>PROCESSING JOBS</span>
                    <h2>Live source pipeline</h2>
                  </div>
                  <Link href="/documents">Open sources</Link>
                </div>
                <div>
                  {data.processing_jobs.map((job) => (
                    <article key={`${job.kind}-${job.id}`}>
                      <i>△</i>
                      <div>
                        <strong>{job.source_name ?? "Private source"}</strong>
                        <span>
                          {job.kind} ·{" "}
                          {(job.stage ?? job.status).replaceAll("_", " ")}
                          {job.attempt ? ` · attempt ${job.attempt}/3` : ""}
                        </span>
                      </div>
                      <em>{job.status}</em>
                      {(job.can_cancel || job.can_retry) && <div className="job-actions">
                        {job.can_cancel && <button disabled={jobBusy === job.id} onClick={() => void controlJob(job.id, "cancel")} aria-label={`Cancel ${job.source_name ?? job.kind}`}><Square size={12} /></button>}
                        {job.can_retry && <button disabled={jobBusy === job.id} onClick={() => void controlJob(job.id, "retry")} aria-label={`Retry ${job.source_name ?? job.kind}`}><RefreshCw className={jobBusy === job.id ? "spin" : ""} size={13} /></button>}
                      </div>}
                    </article>
                  ))}
                </div>
              </section>
            </Reveal>
          )}
        </>
      )}
      <WorkspaceDialog
        open={createOpen}
        setOpen={setCreateOpen}
        title="Create a source collection"
        description="Group related documents, websites and conversations in one private place."
        value={name}
        setValue={setName}
        action={() => void create()}
        actionLabel={busy ? "Creating…" : "Create"}
        disabled={busy || name.trim().length < 2}
      />
      <WorkspaceDialog
        open={Boolean(renameTarget)}
        setOpen={(open) => {
          if (!open) setRenameTarget(null);
        }}
        title="Rename collection"
        description="Update the name without changing its private sources."
        value={renameTarget?.name ?? ""}
        setValue={(value) =>
          setRenameTarget((target) =>
            target ? { ...target, name: value } : null,
          )
        }
        action={() => void rename()}
        actionLabel="Save"
        disabled={busy || (renameTarget?.name.trim().length ?? 0) < 2}
      />
      <Dialog.Root
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="citation-overlay" />
          <Dialog.Content className="workspace-dialog danger">
            <Dialog.Title>Delete “{deleteTarget?.name}”?</Dialog.Title>
            <Dialog.Description>
              Documents, websites, vectors, derived artifacts, files and caches
              will be permanently removed.
            </Dialog.Description>
            <div>
              <Dialog.Close asChild>
                <Button variant="secondary">Cancel</Button>
              </Dialog.Close>
              <Button
                variant="destructive"
                onClick={() => void remove()}
                disabled={busy}
              >
                {busy ? "Deleting securely…" : "Delete collection"}
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

function WorkspaceDialog({
  open,
  setOpen,
  title,
  description,
  value,
  setValue,
  action,
  actionLabel,
  disabled,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
  title: string;
  description: string;
  value: string;
  setValue: (value: string) => void;
  action: () => void;
  actionLabel: string;
  disabled: boolean;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="citation-overlay" />
        <Dialog.Content className="workspace-dialog">
          <Dialog.Title>{title}</Dialog.Title>
          <Dialog.Description>{description}</Dialog.Description>
          <label>
            Workspace name
            <input
              autoFocus
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !disabled) action();
              }}
              placeholder="e.g. Machine Learning"
            />
          </label>
          <div>
            <Dialog.Close asChild>
              <Button variant="secondary">Cancel</Button>
            </Dialog.Close>
            <Button onClick={action} disabled={disabled}>
              {actionLabel}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

"use client";

import {
  AlertTriangle,
  Check,
  FileImage,
  FileText,
  FolderPlus,
  LoaderCircle,
  RefreshCw,
  Search,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import Link from "next/link";
import {
  ChangeEvent,
  DragEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { Reveal } from "@/components/animations/reveal";
import { Button } from "@/components/ui/button";
import {
  createWorkspace,
  deleteDocument,
  type DocumentItem,
  listDocuments,
  listWorkspaces,
  reindexDocument,
  uploadDocuments,
  type Workspace,
} from "@/services/document.service";

const allowed = [".pdf", ".docx", ".txt", ".md", ".jpg", ".jpeg", ".png"];
const activeStates = new Set([
  "queued",
  "validating",
  "security_check",
  "extracting",
  "ocr",
  "cleaning",
  "chunking",
  "embedding",
  "indexing",
]);
const stateLabel: Record<string, string> = {
  queued: "Queued",
  validating: "Validating",
  security_check: "Security check",
  extracting: "Extracting text",
  ocr: "Reading with OCR",
  cleaning: "Cleaning text",
  chunking: "Smart chunking",
  embedding: "Creating embeddings",
  indexing: "Secure indexing",
  completed: "Ready",
  failed: "Failed",
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
function iconFor(name: string) {
  return /\.(jpg|jpeg|png)$/i.test(name) ? FileImage : FileText;
}

export default function DocumentsPage() {
  const input = useRef<HTMLInputElement>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newWorkspace, setNewWorkspace] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(
    async (target = workspaceId) => {
      try {
        setDocuments(await listDocuments(target || undefined));
        setError("");
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not load documents.",
        );
      }
    },
    [workspaceId],
  );

  useEffect(() => {
    void (async () => {
      try {
        const items = await listWorkspaces();
        setWorkspaces(items);
        const requested = new URLSearchParams(window.location.search).get(
          "workspace",
        );
        const first = items.some((item) => item.id === requested)
          ? requested!
          : (items[0]?.id ?? "");
        setWorkspaceId(first);
        if (first) setDocuments(await listDocuments(first));
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not load your collection.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  useEffect(() => {
    if (!documents.some((item) => activeStates.has(item.status))) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 5_000);
    return () => window.clearInterval(timer);
  }, [documents, refresh]);

  function acceptFiles(incoming: File[]) {
    const valid = incoming
      .filter(
        (file) =>
          allowed.some((extension) =>
            file.name.toLowerCase().endsWith(extension),
          ) &&
          file.size > 0 &&
          file.size <= 25 * 1024 * 1024,
      )
      .slice(0, 10);
    setSelected(valid);
    setError(
      valid.length === incoming.length
        ? ""
        : "Some files were rejected. Use supported non-empty files up to 25 MB.",
    );
  }
  function choose(event: ChangeEvent<HTMLInputElement>) {
    acceptFiles(Array.from(event.target.files ?? []));
  }
  function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    acceptFiles(Array.from(event.dataTransfer.files));
  }

  async function upload() {
    if (!workspaceId || !selected.length) return;
    setBusy(true);
    setError("");
    try {
      const queued = await uploadDocuments(workspaceId, selected);
      setDocuments((items) => [...queued, ...items]);
      setSelected([]);
      if (input.current) input.current.value = "";
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }
  async function addWorkspace() {
    if (newWorkspace.trim().length < 2) return;
    setCreating(true);
    try {
      const item = await createWorkspace(newWorkspace.trim());
      setWorkspaces((items) => [item, ...items]);
      setWorkspaceId(item.id);
      setDocuments([]);
      setNewWorkspace("");
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not create workspace.",
      );
    } finally {
      setCreating(false);
    }
  }
  async function remove(id: string) {
    try {
      await deleteDocument(id);
      setDocuments((items) => items.filter((item) => item.id !== id));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not delete document.",
      );
    }
  }
  async function retry(id: string) {
    try {
      await reindexDocument(id);
      await refresh();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not restart processing.",
      );
    }
  }

  return (
    <div className="documents-page">
      <Reveal>
        <header className="page-heading">
          <div>
            <span className="page-kicker">YOUR FILES, SEARCHABLE</span>
            <h1>Documents</h1>
            <p>
              Upload a file, wait until it says Ready, then ask accurate
              questions from its content.
            </p>
          </div>
          <div className="workspace-picker">
            <select
              value={workspaceId}
              onChange={(event) => {
                setWorkspaceId(event.target.value);
                void refresh(event.target.value);
              }}
              aria-label="Document collection"
            >
              <option value="">Select collection</option>
              {workspaces.map((item) => (
                <option value={item.id} key={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
        </header>
      </Reveal>
      <section className="flow-explainer">
        <span>
          <b>1</b> Choose a collection
        </span>
        <span>
          <b>2</b> Upload documents
        </span>
        <span>
          <b>3</b> Wait for Ready
        </span>
        <span>
          <b>4</b> Ask in Chat
        </span>
      </section>
      {error && (
        <div className="document-alert" role="alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss error">
            <X size={15} />
          </button>
        </div>
      )}
      {!loading && workspaces.length === 0 && (
        <section className="workspace-create">
          <FolderPlus size={21} />
          <div>
            <strong>Create your first collection</strong>
            <span>
              A collection simply keeps related documents and websites together.
            </span>
          </div>
          <input
            value={newWorkspace}
            onChange={(event) => setNewWorkspace(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void addWorkspace();
            }}
            placeholder="Example: College notes"
            aria-label="New collection name"
          />
          <Button
            onClick={() => void addWorkspace()}
            disabled={creating || newWorkspace.trim().length < 2}
          >
            {creating ? "Creating…" : "Create collection"}
          </Button>
        </section>
      )}
      <div className="document-layout">
        <Reveal className="upload-column">
          <section
            className={`upload-zone ${dragging ? "dragging" : ""}`}
            onDragEnter={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={drop}
          >
            <input
              ref={input}
              type="file"
              multiple
              accept={allowed.join(",")}
              onChange={choose}
            />
            <div className="upload-geometry">
              <UploadCloud size={27} />
              <span />
              <span />
              <span />
            </div>
            <h2>
              {dragging ? "Release to upload" : "Drop documents here"}
            </h2>
            <p>
              PDF, DOCX, TXT, Markdown, JPG or PNG · up to 10 files · 25 MB each
            </p>
            <Button variant="secondary" onClick={() => input.current?.click()}>
              Choose files
            </Button>
            <small>
              Files remain private and are never placed in a public directory.
            </small>
          </section>
          {selected.length > 0 && (
            <section className="upload-queue">
              <div className="upload-queue-head">
                <div>
                  <strong>
                    {selected.length} file{selected.length > 1 ? "s" : ""} ready
                  </strong>
                  <span>Real processing begins after upload</span>
                </div>
                <button onClick={() => setSelected([])}>Clear</button>
              </div>
              {selected.map((file, index) => {
                const Icon = iconFor(file.name);
                return (
                  <div
                    className="queued-file"
                    key={`${file.name}-${file.size}`}
                  >
                    <Icon size={18} />
                    <div>
                      <strong>{file.name}</strong>
                      <span>{formatBytes(file.size)}</span>
                    </div>
                    <button
                      onClick={() =>
                        setSelected((items) =>
                          items.filter((_, itemIndex) => itemIndex !== index),
                        )
                      }
                      aria-label={`Remove ${file.name}`}
                    >
                      <X size={15} />
                    </button>
                  </div>
                );
              })}
              <Button
                onClick={() => void upload()}
                disabled={busy || !workspaceId}
              >
                {busy ? (
                  <>
                    <LoaderCircle className="spin" size={17} /> Uploading…
                  </>
                ) : (
                  <>
                    <UploadCloud size={17} /> Upload and process
                  </>
                )}
              </Button>
            </section>
          )}
        </Reveal>
        <Reveal className="library-column" delay={0.06}>
          <section className="document-library">
            <div className="document-library-head">
              <div>
                <span>YOUR COLLECTION</span>
                <h2>Uploaded documents</h2>
              </div>
              <div className="library-head-actions">
                {workspaceId && documents.some((item) => item.status === "completed") && (
                  <Link href={`/chat?workspace=${workspaceId}&mode=knowledge`}>Ask documents</Link>
                )}
                <button onClick={() => void refresh()} aria-label="Refresh documents">
                  <RefreshCw size={16} />
                </button>
              </div>
            </div>
            <div className="document-filter">
              <Search size={15} />
              <span>
                {documents.length
                  ? `${documents.length} document${documents.length > 1 ? "s" : ""}`
                  : "No documents indexed"}
              </span>
            </div>
            {loading ? (
              <div className="document-skeletons">
                {[0, 1, 2].map((item) => (
                  <span key={item} />
                ))}
              </div>
            ) : documents.length === 0 ? (
              <div className="document-empty">
                <div>△</div>
                <strong>No documents yet</strong>
                <p>Upload a supported file, then ask questions from Chat.</p>
              </div>
            ) : (
              <div className="document-list">
                {documents.map((item) => {
                  const Icon = iconFor(item.original_name);
                  const active = activeStates.has(item.status);
                  return (
                    <article className="document-row" key={item.id}>
                      <div className="document-type">
                        <Icon size={19} />
                      </div>
                      <div className="document-info">
                        <strong title={item.original_name}>
                          {item.original_name}
                        </strong>
                        <span>
                          {formatBytes(item.size_bytes)}
                          {item.page_count
                            ? ` · ${item.page_count} page${item.page_count > 1 ? "s" : ""}`
                            : ""}
                          {item.chunk_count
                            ? ` · ${item.chunk_count} chunks`
                            : ""}
                          {item.ocr_used ? " · OCR" : ""}
                        </span>
                        <div className={`processing-state ${item.status}`}>
                          <i>
                            {active ? (
                              <LoaderCircle className="spin" size={12} />
                            ) : item.status === "completed" ? (
                              <Check size={12} />
                            ) : (
                              <AlertTriangle size={12} />
                            )}
                          </i>
                          {stateLabel[item.status] ?? item.status}
                        </div>
                        {item.error_message && (
                          <small>{item.error_message}</small>
                        )}
                      </div>
                      <div className="document-actions">
                        {item.status === "completed" && (
                          <Link
                            href={`/chat?workspace=${workspaceId}&mode=knowledge&document=${item.id}`}
                            aria-label={`Ask questions about ${item.original_name}`}
                            title="Ask this document"
                          >
                            Ask
                          </Link>
                        )}
                        {item.status === "failed" && (
                          <button
                            onClick={() => void retry(item.id)}
                            aria-label={`Retry ${item.original_name}`}
                          >
                            <RefreshCw size={15} />
                          </button>
                        )}
                        <button
                          onClick={() => void remove(item.id)}
                          aria-label={`Delete ${item.original_name}`}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                      <span className="corner-triangle" />
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </Reveal>
      </div>
    </div>
  );
}

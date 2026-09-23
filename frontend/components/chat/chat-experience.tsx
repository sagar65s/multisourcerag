"use client";

import {
  Archive,
  ArrowUp,
  Bookmark,
  ChevronDown,
  Clipboard,
  Download,
  Globe2,
  Languages,
  Mic,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { AssistantMessage } from "@/components/chat/assistant-message";
import { RagIndicator, type RagStage } from "@/components/chat/rag-indicator";
import {
  CitationDrawer,
  type Citation,
} from "@/components/citations/citation-drawer";
import { Button } from "@/components/ui/button";
import { useVoice } from "@/hooks/use-voice";
import { getUserSettings } from "@/services/account.service";
import { streamChat } from "@/services/chat.service";
import {
  getConversation,
  listConversationMessages,
} from "@/services/conversation.service";
import {
  listDocuments,
  listWorkspaces,
  type DocumentItem,
  type Workspace,
} from "@/services/document.service";
import {
  listWebsites,
  type WebsiteSource,
} from "@/services/website.service";
import { downloadExport, type ExportFormat } from "@/services/export.service";
import {
  saveAnswer,
  saveBookmark,
  sendFeedback,
} from "@/services/saved.service";

const suggestions = [
  "Explain a difficult topic in simple words",
  "Summarize my uploaded documents",
  "What are today's important AI updates?",
];
type EvidenceStatus =
  | "strongly_supported"
  | "supported"
  | "limited_evidence"
  | "no_evidence"
  | "conflicting_evidence"
  | "general_answer"
  | null;
type ChatMode = "auto" | "general" | "knowledge" | "website" | "web" | "both";
type Message = {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sources?: Citation[];
  evidenceStatus?: EvidenceStatus;
  feedback?: "helpful" | "not_helpful";
  saved?: boolean;
};

export function ChatExperience() {
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<RagStage>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [feedbackTarget, setFeedbackTarget] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [websites, setWebsites] = useState<WebsiteSource[]>([]);
  const [sourceChoice, setSourceChoice] = useState("all");
  const [mode, setMode] = useState<ChatMode>("auto");
  const [language, setLanguage] = useState<"English" | "Tamil" | "Hindi">(
    "English",
  );
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("pdf");
  const controller = useRef<AbortController | null>(null);
  const voice = useVoice(language);
  const privateModeNeedsWorkspace = !["auto", "general", "web"].includes(mode);
  const loadSources = useCallback(async (targetWorkspace: string) => {
    if (!targetWorkspace) {
      setDocuments([]);
      setWebsites([]);
      setSourceChoice("all");
      return;
    }
    const [documentItems, websiteItems] = await Promise.all([
      listDocuments(targetWorkspace),
      listWebsites(targetWorkspace),
    ]);
    setDocuments(documentItems.filter((item) => item.status === "completed"));
    setWebsites(websiteItems.filter((item) => item.status === "completed"));
  }, []);
  useEffect(() => {
    void (async () => {
      try {
        const [items, preferences] = await Promise.all([
          listWorkspaces(),
          getUserSettings().catch(() => null),
        ]);
        setWorkspaces(items);
        const params = new URLSearchParams(window.location.search);
        const id = params.get("conversation");
        if (id) {
          const [conversation, stored] = await Promise.all([
            getConversation(id),
            listConversationMessages(id),
          ]);
          setConversationId(id);
          setWorkspaceId(conversation.workspace_id ?? "");
          if (conversation.workspace_id) await loadSources(conversation.workspace_id);
          const requestedDocument = params.get("document");
          const requestedWebsite = params.get("website");
          if (requestedDocument) setSourceChoice(`document:${requestedDocument}`);
          if (requestedWebsite) setSourceChoice(`website:${requestedWebsite}`);
          setMode(conversation.mode);
          setLanguage(conversation.language);
          setMessages(
            stored.map((item) => ({
              id: item.id,
              role: item.role,
              content: item.content,
              sources: item.sources,
              evidenceStatus: item.evidence_status,
            })),
          );
        } else {
          const requestedWorkspace = params.get("workspace") ?? "";
          const requestedMode = params.get("mode") as ChatMode | null;
          const validWorkspace = items.some((item) => item.id === requestedWorkspace)
            ? requestedWorkspace
            : (items[0]?.id ?? "");
          setWorkspaceId(validWorkspace);
          if (validWorkspace) await loadSources(validWorkspace);
          if (
            ["auto", "general", "knowledge", "website", "web", "both"].includes(
              requestedMode ?? "",
            )
          )
            setMode(requestedMode!);
          const prompt = params.get("prompt");
          if (prompt) setQuery(prompt.slice(0, 8000));
          const requestedDocument = params.get("document");
          const requestedWebsite = params.get("website");
          if (requestedDocument) setSourceChoice(`document:${requestedDocument}`);
          if (requestedWebsite) setSourceChoice(`website:${requestedWebsite}`);
          const preferred =
            preferences?.language ??
            localStorage.getItem("multisource-language");
          if (
            preferred === "English" ||
            preferred === "Tamil" ||
            preferred === "Hindi"
          )
            setLanguage(preferred);
        }
      } catch (reason) {
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not load chat history.",
        );
      }
    })();
  }, [loadSources]);
  async function send(override?: string) {
    const question = (override ?? query).trim();
    if (
      !question ||
      (privateModeNeedsWorkspace && !workspaceId) ||
      stage !== "idle"
    )
      return;
    setQuery("");
    setError("");
    setNotice("");
    setStage("understanding");
    const abort = new AbortController();
    controller.current = abort;
    setMessages((items) => [
      ...items,
      { role: "user", content: question },
      { role: "assistant", content: "", sources: [], evidenceStatus: null },
    ]);
    try {
      const selectedDocumentIds = sourceChoice.startsWith("document:")
        ? [sourceChoice.slice("document:".length)]
        : [];
      const selectedWebsiteIds = sourceChoice.startsWith("website:")
        ? [sourceChoice.slice("website:".length)]
        : [];
      await streamChat(
        question,
        workspaceId,
        mode,
        language,
        ({ event, data }) => {
          if (event === "conversation") {
            const id = String(data.conversation_id);
            setConversationId(id);
            const selectedSource = sourceChoice.startsWith("document:")
              ? `&document=${encodeURIComponent(sourceChoice.slice("document:".length))}`
              : sourceChoice.startsWith("website:")
                ? `&website=${encodeURIComponent(sourceChoice.slice("website:".length))}`
                : "";
            window.history.replaceState(null, "", `/chat?conversation=${id}${selectedSource}`);
          }
          if (event === "stage")
            setStage((data.stage as RagStage) ?? "understanding");
          if (event === "sources")
            setMessages((items) =>
              items.map((item, index) =>
                index === items.length - 1
                  ? {
                      ...item,
                      sources: data.sources as Citation[],
                      evidenceStatus: data.evidence_status as EvidenceStatus,
                    }
                  : item,
              ),
            );
          if (event === "token") {
            setMessages((items) =>
              items.map((item, index) =>
                index === items.length - 1
                  ? { ...item, content: item.content + String(data.text ?? "") }
                  : item,
              ),
            );
          }
          if (event === "message")
            setMessages((items) =>
              items.map((item, index) =>
                index === items.length - 1
                  ? { ...item, id: String(data.message_id) }
                  : item,
              ),
            );
          if (event === "error")
            setError(String(data.message ?? "Generation failed"));
          if (event === "complete")
            setMessages((items) =>
              items.map((item, index) =>
                index === items.length - 1
                  ? {
                      ...item,
                      sources:
                        (data.sources as Citation[] | undefined) ??
                        item.sources,
                      evidenceStatus: data.evidence_status as EvidenceStatus,
                    }
                  : item,
              ),
            );
          if (event === "complete" || event === "error") setStage("idle");
        },
        abort.signal,
        conversationId,
        selectedDocumentIds,
        selectedWebsiteIds,
      );
    } catch (reason) {
      if (!abort.signal.aborted) {
        setError(
          reason instanceof Error
            ? reason.message
            : "The request could not be completed.",
        );
        setMessages((items) => items.filter((item, index) => index !== items.length - 1 || item.content.trim() || item.id));
      }
      setStage("idle");
    } finally {
      controller.current = null;
    }
  }
  const assistantAction = async (
    action: "save" | "helpful" | "not_helpful" | "bookmark",
    message: Message,
    sourceId?: string,
    reasons: string[] = [],
  ) => {
    if (!message.id) return;
    try {
      if (action === "save") {
        await saveAnswer(message.id);
        setMessages((items) =>
          items.map((item) =>
            item.id === message.id ? { ...item, saved: true } : item,
          ),
        );
        setNotice("Answer saved with its citations.");
      }
      if (action === "helpful" || action === "not_helpful") {
        await sendFeedback(message.id, action === "helpful", reasons);
        setMessages((items) =>
          items.map((item) =>
            item.id === message.id ? { ...item, feedback: action } : item,
          ),
        );
        setFeedbackTarget(null);
        setNotice("Feedback recorded securely.");
      }
      if (action === "bookmark" && sourceId) {
        await saveBookmark(message.id, sourceId);
        setNotice(`${sourceId} bookmarked.`);
      }
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not complete this action.",
      );
    }
  };
  const stop = () => {
    controller.current?.abort();
    controller.current = null;
    setStage("idle");
    setNotice("Generation stopped.");
  };
  return (
    <div className="chat-page">
      <header className="chat-header">
        <div>
          <span>MULTISOURCE AI</span>
          <h1>Ask anything</h1>
        </div>
        <div className="chat-head-actions">
          {conversationId && (
            <>
              <select
                value={exportFormat}
                onChange={(event) =>
                  setExportFormat(event.target.value as ExportFormat)
                }
                aria-label="Export format"
              >
                <option value="pdf">PDF</option>
                <option value="docx">DOCX</option>
                <option value="markdown">Markdown</option>
                <option value="txt">TXT</option>
              </select>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Export conversation"
                onClick={() =>
                  void downloadExport(
                    "conversation",
                    conversationId,
                    exportFormat,
                  ).catch((reason) => setError(reason.message))
                }
              >
                <Download size={16} />
              </Button>
            </>
          )}
          <div className="privacy-state">
            <ShieldCheck size={15} /> Private by default
          </div>
        </div>
      </header>
      {error && (
        <div className="chat-error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="chat-notice" role="status">
          {notice}
        </div>
      )}
      <div className="chat-canvas">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="assistant-orb">
              <Sparkles size={26} />
            </div>
            <h2>What do you want to understand?</h2>
            <p>
              Chat normally, ask your documents, analyze a website, or check the
              live web.
            </p>
            <div className="suggestion-list">
              {suggestions.map((item) => (
                <button key={item} onClick={() => setQuery(item)}>
                  {item}
                  <span>↗</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message, index) => (
              <article
                key={message.id ?? index}
                className={`message ${message.role}`}
              >
                <span>{message.role === "assistant" ? "△" : "You"}</span>
                {message.role === "assistant" ? (
                  <div className="message-answer">
                    <AssistantMessage
                      content={message.content}
                      sources={message.sources ?? []}
                      onCitation={setActiveCitation}
                    />
                    {message.evidenceStatus && (
                      <span
                        className={`evidence-badge ${message.evidenceStatus}`}
                      >
                        {message.evidenceStatus.replaceAll("_", " ")}
                      </span>
                    )}
                    {message.id && (
                      <div className="message-tools">
                        <button
                          onClick={() =>
                            void navigator.clipboard.writeText(message.content)
                          }
                          aria-label="Copy answer"
                        >
                          <Clipboard size={14} />
                          <span>Copy</span>
                        </button>
                        <button
                          className={message.saved ? "active" : ""}
                          onClick={() => void assistantAction("save", message)}
                          aria-label="Save answer"
                        >
                          <Archive size={14} />
                          <span>Save</span>
                        </button>
                        <button
                          onClick={() =>
                            voice.state === "speaking" &&
                            voice.activeId === (message.id ?? `answer-${index}`)
                              ? voice.stopSpeaking()
                              : voice.speak(
                                  message.content,
                                  message.id ?? `answer-${index}`,
                                )
                          }
                          aria-label={
                            voice.state === "speaking" &&
                            voice.activeId === (message.id ?? `answer-${index}`)
                              ? "Stop this answer"
                              : "Listen to this answer"
                          }
                        >
                          {voice.state === "speaking" &&
                          voice.activeId === message.id ? (
                            <VolumeX size={14} />
                          ) : (
                            <Volume2 size={14} />
                          )}
                          <span>Listen</span>
                        </button>
                        <button
                          className={
                            message.feedback === "helpful" ? "active" : ""
                          }
                          onClick={() =>
                            void assistantAction("helpful", message)
                          }
                          aria-label="Helpful"
                        >
                          <ThumbsUp size={14} />
                          <span>Helpful</span>
                        </button>
                        <button
                          className={
                            message.feedback === "not_helpful" ? "active" : ""
                          }
                          onClick={() =>
                            setFeedbackTarget((value) =>
                              value === message.id
                                ? null
                                : (message.id ?? null),
                            )
                          }
                          aria-label="Not helpful"
                        >
                          <ThumbsDown size={14} />
                          <span>Improve</span>
                        </button>
                        <button
                          onClick={() => {
                            const previous = messages
                              .slice(0, index)
                              .reverse()
                              .find((item) => item.role === "user");
                            if (previous) void send(previous.content);
                          }}
                          aria-label="Regenerate answer"
                        >
                          <RotateCcw size={14} />
                          <span>Retry</span>
                        </button>
                        {message.sources?.map((source) => (
                          <button
                            key={source.id}
                            onClick={() =>
                              void assistantAction(
                                "bookmark",
                                message,
                                source.id,
                              )
                            }
                            aria-label={`Bookmark ${source.id}`}
                          >
                            <Bookmark size={13} />
                            <small>{source.id}</small>
                          </button>
                        ))}
                      </div>
                    )}
                    {feedbackTarget === message.id && (
                      <div className="feedback-reasons">
                        <span>What should improve?</span>
                        {[
                          ["incorrect", "Incorrect"],
                          ["outdated", "Outdated"],
                          ["irrelevant", "Irrelevant"],
                          ["missing_citation", "Missing citation"],
                          ["incomplete", "Incomplete"],
                        ].map(([id, label]) => (
                          <button
                            key={id}
                            onClick={() =>
                              void assistantAction(
                                "not_helpful",
                                message,
                                undefined,
                                [id],
                              )
                            }
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <p>{message.content}</p>
                )}
              </article>
            ))}
          </div>
        )}
        <RagIndicator stage={stage} />
      </div>
      <div className="composer-wrap">
        {(voice.state !== "idle" || stage !== "idle") && (
          <div
            className={`voice-status ${voice.state === "listening" ? "listening" : stage !== "idle" ? "processing" : voice.state}`}
          >
            <div>
              <span />
              <span />
              <span />
              <span />
            </div>
            <strong>
              {voice.state === "listening"
                ? "Listening…"
                : voice.state === "speaking"
                  ? "Speaking…"
                  : stage !== "idle"
                    ? "Processing…"
                    : "Voice unavailable"}
            </strong>
          </div>
        )}
        <div className="composer">
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send();
              }
            }}
            placeholder="Ask anything…"
            aria-label="Chat message"
            rows={1}
          />
          <div className="composer-actions">
            <div className="composer-source-controls">
              <label className="composer-select">
                <Globe2 size={15} />
                <span className="select-field-copy">
                  <small>1. Collection</small>
                  <strong>{workspaces.find((item) => item.id === workspaceId)?.name ?? "Choose collection"}</strong>
                </span>
                <select
                  value={workspaceId}
                  onChange={(event) => {
                    const nextWorkspace = event.target.value;
                    setWorkspaceId(nextWorkspace);
                    setSourceChoice("all");
                    void loadSources(nextWorkspace).catch((reason) =>
                      setError(reason instanceof Error ? reason.message : "Could not load sources."),
                    );
                  }}
                  aria-label="Document collection"
                  disabled={Boolean(conversationId)}
                >
                  <option value="">Choose a collection</option>
                  {workspaces.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
                <ChevronDown size={13} />
              </label>
              {workspaceId && (
                <label className="composer-select source-select">
                  <Archive size={15} />
                  <span className="select-field-copy">
                    <small>2. Answer from</small>
                    <strong>
                      {sourceChoice.startsWith("document:")
                        ? documents.find((item) => `document:${item.id}` === sourceChoice)?.original_name ?? "Selected document"
                        : sourceChoice.startsWith("website:")
                          ? websites.find((item) => `website:${item.id}` === sourceChoice)?.title ?? "Selected website"
                          : mode === "website"
                            ? "All indexed websites"
                            : "All ready documents"}
                    </strong>
                  </span>
                  <select
                    value={sourceChoice}
                    onChange={(event) => {
                      const value = event.target.value;
                      setSourceChoice(value);
                      if (value.startsWith("document:")) setMode("knowledge");
                      if (value.startsWith("website:")) setMode("website");
                    }}
                    aria-label="Answer source"
                  >
                    <option value="all">
                      {mode === "website"
                        ? "All indexed websites"
                        : mode === "both"
                          ? "All collection sources"
                          : "All ready documents"}
                    </option>
                    {documents.length > 0 && (
                      <optgroup label="Documents">
                        {documents.map((item) => (
                          <option value={`document:${item.id}`} key={item.id}>
                            {item.original_name} · {item.page_count} pages
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {websites.length > 0 && (
                      <optgroup label="Websites">
                        {websites.map((item) => (
                          <option value={`website:${item.id}`} key={item.id}>
                            {item.title || item.domain}
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                  <ChevronDown size={13} />
                </label>
              )}
              <label className="mode-select">
                <Sparkles size={15} />
                <span className="select-field-copy">
                  <small>Answer mode</small>
                  <strong>
                    {mode === "auto" ? "Smart chat" : mode === "general" ? "General" : mode === "knowledge" ? "Documents" : mode === "website" ? "Website" : mode === "web" ? "Live web" : "Documents + web"}
                  </strong>
                </span>
                <select
                  value={mode}
                  onChange={(event) => setMode(event.target.value as ChatMode)}
                  aria-label="Research mode"
                >
                  <option value="auto">Smart chat</option>
                  <option value="general">General only</option>
                  <option value="knowledge">My documents</option>
                  <option value="website">Indexed website</option>
                  <option value="web">Live web</option>
                  <option value="both">Both</option>
                </select>
                <ChevronDown size={12} />
              </label>
            </div>
            <div className="composer-submit-controls">
              <label className="language-select">
                <Languages size={15} />
                <span>Language</span>
                <select
                  value={language}
                  onChange={(event) =>
                    setLanguage(event.target.value as typeof language)
                  }
                  aria-label="Answer language"
                >
                  <option>English</option>
                  <option>Tamil</option>
                  <option>Hindi</option>
                </select>
              </label>
              <Button
                variant={voice.state === "listening" ? "secondary" : "ghost"}
                size="icon"
                aria-label={
                  voice.state === "listening"
                    ? "Stop listening"
                    : "Use microphone"
                }
                onClick={() =>
                  voice.state === "listening"
                    ? voice.stopListening()
                    : voice.startListening(setQuery)
                }
              >
                {voice.state === "listening" ? (
                  <Square size={15} />
                ) : (
                  <Mic size={18} />
                )}
              </Button>
              {stage !== "idle" ? (
                <Button
                  variant="destructive"
                  size="icon"
                  aria-label="Stop generation"
                  onClick={stop}
                >
                  <Square size={15} />
                </Button>
              ) : (
                <Button
                  size="icon"
                  aria-label="Send message"
                  onClick={() => void send()}
                  disabled={
                    !query.trim() || (privateModeNeedsWorkspace && !workspaceId)
                  }
                >
                  <ArrowUp size={18} />
                </Button>
              )}
            </div>
          </div>
        </div>
        <p>
          {voice.error ||
            "Use the speaker button below any AI answer to listen. Voice audio is not stored."}
        </p>
      </div>
      <CitationDrawer
        citation={activeCitation}
        onClose={() => setActiveCitation(null)}
      />
    </div>
  );
}

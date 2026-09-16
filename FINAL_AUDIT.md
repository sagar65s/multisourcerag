# MultiSource AI final audit

Verified release audit date: 2026-09-16

## 2026-09-16 source-grounding update

Chat now sends the exact selected document or indexed website ID to the backend and preserves that selection in the conversation URL. The backend verifies source ownership and workspace membership before retrieval. PDF page references in English, Tamil, and Hindi route directly to the requested page chunks; document-summary questions sample the document from beginning to end. Dense and lexical retrieval degrade independently, so Qdrant unavailability does not discard MongoDB evidence.

Website vector payload ownership now matches the Qdrant authorization filter while retaining compatibility with already indexed points. Public GitHub repository URLs use a dedicated API-based ingestion path that records repository metadata, README, languages, license, activity statistics, and a bounded file tree. Generic public-site crawling retains SSRF, redirect, robots, response-size, and optional browser-rendering controls.

All validation gates below were rerun on this revision. Actual provider, Firebase, MongoDB Atlas, Qdrant, GitHub rate-limit, and target-website behavior still depends on the deployment owner's credentials and network.

Release decision: **the application code and local packaging are verified. External service acceptance remains dependent on the owner's real credentials and network.**

## Verified release gates

| Gate | Result |
| --- | --- |
| Backend tests | 130 passed, including exact-page retrieval, selected-source isolation, GitHub repository ingestion, SSE, security, and website fetch regressions |
| MongoDB lifecycle | A successful ping keeps the database online even when optional index maintenance must be deferred; true outages retry automatically |
| Python dependencies | `pip check` clean |
| Frontend lint and TypeScript | Passed |
| Accessibility contract audit | Passed |
| Production frontend build | 13 application routes plus not-found generated successfully; Compare, Timeline, and the separate Knowledge page are absent |
| Browser regression | 9 Chromium tests passed across mobile, tablet, and desktop |
| Dependency health | Python `pip check` clean; npm audit reports 0 vulnerabilities |
| Per-answer audio | Speaker reads only the selected AI answer; stop, chunking, cleanup, Tamil/Hindi detection verified |
| Responsive UI | Global readable type floor, labelled chat tools, collection onboarding, premium cards/motion, and mobile/tablet/desktop visual baselines passed |
| Packaging | Source, configuration templates, tests, documentation, and operations scripts included |
| Container dependency | No container runtime files required |

## Document and website grounding resolution

The earlier chat UI selected only a workspace and mode. It did not send the clicked PDF or website ID, so retrieval could search unrelated sources in the same collection. The updated **Answer from** selector lists ready documents with page counts and ready websites, sends separate `document_ids` and `website_ids`, and restores the choice after reload.

PDF questions such as `page 42`, `42 page`, `பக்கம் 42`, and `पृष्ठ 42` use exact page filters. Broader summaries sample chunks across the selected source rather than only the first matching passage. MongoDB text search has an owner-scoped regex fallback when an Atlas text index is unavailable.

Website and GitHub chunks are written to MongoDB before optional embedding/vector indexing. This keeps grounded lexical Q&A available when the embedding model or Qdrant is temporarily unavailable. Both legacy `owner_id` and current `user_id` vector payloads remain strictly owner-scoped during retrieval and deletion.

## MongoDB failure resolution

The reported Atlas `TLSV1_ALERT_INTERNAL_ERROR` happens before MongoDB authentication completes and is commonly caused by Atlas IP access, VPN/antivirus TLS inspection, firewall/ISP port filtering, or a stale connection URI. The client keeps TLS certificate verification enabled and uses the current CA bundle. A failed external connection no longer terminates FastAPI: liveness stays online, readiness reports the dependency state, background reconnect runs at a bounded interval, and database routes return a safe temporary-unavailable response. MongoDB connectivity and index maintenance are tracked separately, so an existing-index conflict can no longer incorrectly take a healthy connection offline.

No application can guarantee a successful connection while the user's network or Atlas access policy blocks the TLS handshake. The deployment owner must still validate the actual Atlas URI and network.

## Session 503 and chat resolution

The reported `/account/session` 503 was not a MongoDB failure after the successful ping. SlowAPI requires a Starlette `Response` parameter on decorated endpoints when rate-limit headers are enabled. Every affected endpoint now accepts the injected response, and a regression test prevents that startup/session failure from returning.

Chat now defaults to normal general conversation without requiring document citations. Current-information questions route to live web search, document and indexed-website modes remain source-grounded, and verified answers are no longer discarded solely because an AI provider omitted inline citation markers. If selected evidence is unavailable, Chat produces a clearly labelled general-knowledge fallback while explicitly avoiding invented private-source or current claims.

The reported streamed-chat crash was a Python closure error: reassigning the routed `mode` inside the async event generator made the earlier read an uninitialized local variable. The generator now uses an explicitly initialized local `resolved_mode`, and a regression test consumes the stream from its first event through completion. Repository names are also kept distinct from document lookups, preventing the related local-variable shadowing failure.

Website ingestion uses browser-compatible request headers, bounded retry/backoff for transient Render/cold-start and rate-limit responses, safe metadata/noscript/JSON-LD extraction for sparse apps, optional Playwright rendering, and unchanged private-network/redirect/robots protections. Deep-research web queries now run concurrently, and completed reports can be downloaded directly as PDF.

## Credential-dependent acceptance

Before production use, complete these checks with the real accounts:

1. Verify MongoDB Atlas Network Access and Qdrant connectivity.
2. Verify Firebase email/password and Google login with matching Web and Admin projects.
3. Upload text and scanned documents and confirm OCR languages are installed.
4. Run chat, website, live research, citations, exports, and per-answer speech.
5. Confirm two different users cannot access each other's workspaces, documents, vectors, or conversations.
6. Keep secrets only in local `.env` files or a production secret manager.

The release contains no real API keys, passwords, private uploads, dependency caches, or build caches.

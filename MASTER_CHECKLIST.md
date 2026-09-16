# Master implementation checklist

Status keys: `[x]` implemented, `[~]` foundation implemented, `[ ]` scheduled.

## Foundation

- [x] Monorepo configuration and environment templates
- [x] FastAPI lifecycle, health, error envelope, request ID, and security headers
- [x] Firebase Admin token verification dependency
- [x] Firebase session-resolved frontend private-route guard and persistence selection
- [x] Server-derived Firebase account profile sync, login audit, and owner-only account metadata
- [x] Owner-scoped cross-device theme, language, and voice preferences
- [x] MongoDB lifecycle and owner-scoped workspace repository
- [x] Configuration-driven LLM/search provider registries
- [x] Premium Next.js landing page and application shell
- [x] Responsive animated triangle system and reduced-motion support
- [x] SSE chat transport contract and processing-stage UI
- [x] Owner-scoped live dashboard metrics, recent activity, and processing jobs
- [x] Workspace create, rename, cascade delete, and selected-studio navigation
- [x] Persistent queued/processing/completed/failed job records and replaceable dispatcher boundary
- [x] Owner-scoped job cancellation, bounded retry, dashboard controls, and interrupted-worker recovery
- [x] Direct local-terminal runtime, readiness probes, and private storage configuration
- [x] Structured content-free request observability and protected Admin operational health UI
- [x] Configurable TTL retention for operational logs and terminal processing jobs
- [x] Age-encrypted MongoDB/Qdrant/private-file backup and guarded restore workflow
- [x] Deployment-neutral TLS, reverse-proxy, secret-manager, and restricted-datastore production guidance
- [x] Per-answer read-aloud controls in Chat, with English/Tamil/Hindi voice selection, cancellation, privacy disclosure, and reduced-motion UI
- [x] CI quality gates for backend tests, frontend contracts, type checking, and production builds
- [x] LangChain document, recursive-splitting, metadata, and prompt adapter wired into ingestion and chat
- [x] Stage 21 local-runtime release audit with warning-free tests, real CPU embedding smoke test, lint, browser, build, and packaging validation

## Ingestion and retrieval

- [x] Private upload storage and file-signature validation
- [x] PyMuPDF text extraction and selective Tesseract OCR
- [x] DOCX, TXT, Markdown, JPG, JPEG, and PNG loaders
- [x] Structure-aware chunking with complete citation metadata
- [x] Sentence Transformers embedding batches
- [x] Qdrant collections with mandatory user/workspace filters
- [x] Dense plus sparse hybrid retrieval, deduplication, and reranking
- [x] Exact selected-document/website filtering with reload-safe Chat source selection
- [x] Exact PDF page retrieval in English, Tamil, and Hindi plus whole-document sampling
- [x] MongoDB lexical fallback when vector search or Atlas text search is unavailable
- [x] Deletion across MongoDB, Qdrant, private files, chunks, and derived intelligence artifacts

## Website and live research

- [x] SSRF-safe URL validation module
- [x] httpx/BeautifulSoup fetcher and Playwright fallback
- [x] robots.txt-aware bounded crawler and selected-page flow
- [x] Public GitHub repository metadata, README, language, license, statistics, and file-tree ingestion
- [x] Search provider registry
- [x] Tavily and DDGS search implementations
- [x] Authority, freshness, contradiction, and fact-verification pipeline
- [x] Focused deep-research service with private and live-web evidence

## Intelligence and product features

- [x] Automatic query router with freshness, private, website, both, web, and deep-research intent
- [x] Multi-source context builder, secret filtering, citation mapper, and answer verification
- [x] Summaries, notes, FAQs, Q&A, entities, dates, and keywords
- [x] Document upload, OCR, indexing, grounded chat, and exports
- [x] Saved answers, citation bookmarks, searchable history, feedback, and owner-scoped exports
- [x] Browser voice recognition/synthesis with English, Tamil, and Hindi controls
- [x] Admin analytics without private-content exposure
- [x] Provider/search health, cooldown, quota, and content-free telemetry dashboard
- [x] Recent-login protected full account-data deletion

## Security and verification

- [x] CORS allow-list and production error normalization
- [x] Operation-specific chat, upload, crawl, research, intelligence, export, and deletion rate limits
- [x] Secret redaction foundation
- [x] SSRF/private-network checks
- [x] Redirect revalidation and DNS rebinding integration tests
- [x] File/MIME/signature/size/path traversal tests
- [x] Cross-user MongoDB and Qdrant isolation integration tests
- [x] Prompt-injection, deletion, admin, quota, and provider leakage tests
- [x] Production wildcard CORS/trusted-host rejection and datastore readiness tests
- [x] Automated accessibility contract, keyboard, reduced-motion, touch-target, and responsive overflow audit
- [x] Chromium E2E interaction tests and light/dark visual baselines at mobile, tablet, and desktop viewports
- [x] Accessible mobile landing navigation with real section links, Escape close, and expanded-state semantics
- [x] Missing/invalid authentication, empty/oversized upload, and expensive-route rate-limit regression tests

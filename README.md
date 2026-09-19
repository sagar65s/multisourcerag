# MultiSource AI

MultiSource AI is a lightweight, privacy-focused research assistant for chatting with private documents, websites, and live web sources. It uses a Next.js frontend, FastAPI backend, MongoDB Atlas, Qdrant, and Firebase Authentication.

## What is included

- Document upload, OCR, chunking, embeddings, private retrieval, and citations
- A simple **Answer from** selector for one exact PDF or indexed website
- Page-aware PDF questions in English, Tamil, and Hindi (for example: `page 42`, `பக்கம் 42`, or `पृष्ठ 42`)
- Dedicated public GitHub repository indexing for repository metadata, README, languages, license, statistics, and file tree
- Normal AI chat, document-grounded answers, indexed website Q&A, live web search, and deep research
- Persistent conversation history, saved answers, source bookmarks, and exports
- English, Tamil, and Hindi chat input
- A speaker button beneath every assistant answer; clicking it reads only that answer
- Premium responsive UI with a readable type scale, clear controls, motion, and touch-safe layouts
- Owner-scoped MongoDB/Qdrant data isolation and Firebase authentication
- No container runtime dependency

## Simple navigation

**Explore:** Dashboard, Chat, Documents, Websites, Research. **Your library:** Saved and History. Account controls are in Settings. Admin appears only for authorized users. Compare, Timeline, and the separate Knowledge page are intentionally absent.

Dashboard shows the collection setup guide only until you create a collection. For everyday questions choose Chat; a collection is needed only when you want to upload or ask from your private documents and indexed websites. Processing pages refresh only while open, and if a chat stream stops unexpectedly you see a clear retry message instead of a spinner that never ends.

## Required software and services

- Windows 10/11, macOS, or Linux
- Node.js 20 or 22
- Python 3.11 or 3.12
- MongoDB Atlas (or a locally installed MongoDB service)
- Qdrant Cloud (or a locally installed Qdrant service)
- Firebase project
- At least one configured AI provider
- Tesseract 5 for scanned-document OCR

## Windows local setup

Extract this project and open two Command Prompt terminals.

### Terminal 1 — backend

```bat
cd /d D:\path\to\MultiSource-AI\backend
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
notepad .env
uvicorn app.main:app --reload --port 8000
```

Fill `backend/.env` with the MongoDB URI, Qdrant URL/key, Firebase Admin values, and at least one AI-provider key before starting the server.

### Terminal 2 — frontend

```bat
cd /d D:\path\to\MultiSource-AI\frontend
copy .env.example .env.local
notepad .env.local
npm install
npm run dev
```

Fill `frontend/.env.local` with the public Firebase Web values. Never place MongoDB, Qdrant, Firebase Admin, or AI-provider secrets in the frontend file.

Open `http://localhost:3000`. Backend liveness is available at `http://localhost:8000/api/v1/health`, and dependency readiness at `http://localhost:8000/api/v1/health/ready`.

## Simple usage flow

1. On **Dashboard**, click **Create my collection**. A collection is a private folder for related sources and chats.
2. Use **Chat → Smart chat** for normal questions—no collection required. If selected sources contain no matching evidence, Chat gives a clearly labelled general-knowledge answer instead of stopping at an empty response.
3. In **Documents**, select your collection, upload files, and wait for **Ready**. Click the file's **Ask** button. Chat automatically selects that exact file; use **Answer from** to change it. You can ask for any available PDF page directly, such as `Explain page 42`.
4. In **Websites**, choose the same collection, paste either a full URL or a domain such as `chatgpt.com`, and wait for **Ready**. Public Render cold starts and transient 429/503 responses are retried. If a public site returns 403 or an anti-bot page, MultiSource AI does not bypass it: the source falls back to clearly labelled public search-visible summaries and official-domain links. Click its chat button to ask from that exact indexed source. For a public GitHub repository URL, MultiSource AI indexes repository metadata, README, languages, license, statistics, and its file tree through GitHub's public API.
5. Use **Live web** in Chat for current facts, or **Research** for a longer cross-checked report. Completed research has a direct **Download PDF** button.
6. The clearly labelled **Save** action under an answer adds it to **Saved**. Every conversation is automatically available in **History**. The search bar searches this history.

A collection is only a private folder that groups related documents and websites; it is not a separate AI feature.

Websites that require a login, explicitly disallow automated access, expose only a private network address, or enforce an interactive anti-bot challenge are never bypassed. When direct access is blocked, the website card says **public search** and answers are grounded in the indexed public summaries. For JavaScript-only public sites on a machine with enough memory, set `ENABLE_PLAYWRIGHT_FALLBACK=true` and install the browser once with `playwright install chromium` inside the activated backend environment.

Public GitHub repositories work without a token within GitHub's anonymous API limits. If you analyze repositories frequently, create a read-only GitHub token and set `GITHUB_TOKEN` in `backend/.env`; never put that token in `frontend/.env.local`.

## Render deployment

Create separate Render Web Services with root directories `backend` and `frontend`.

For a 512 MiB free backend, use the included lightweight dependency set. It intentionally omits local transformer models, Playwright, and test tools; document and website retrieval use the application's keyword/hash fallback instead of downloading CUDA packages.

```text
Backend root: backend
Build: python -m pip install --upgrade pip && python -m pip install -r requirements-render.txt
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health check: /api/v1/health
PYTHON_VERSION: 3.12.14
WEB_CONCURRENCY: 1
ENABLE_PLAYWRIGHT_FALLBACK: false
```

Use `requirements.txt` locally or on a larger CPU instance for transformer embeddings. Install CPU-only PyTorch before that file; never install CUDA wheels on a CPU Render service.

## MongoDB Atlas TLS/network behavior

If Atlas cannot complete a TLS connection, MultiSource AI now starts in degraded mode instead of crashing. It keeps retrying MongoDB in the background every `MONGODB_RETRY_SECONDS` (30 seconds by default). Liveness remains available, while database-dependent requests receive a controlled `503 Service Unavailable` response until the connection recovers.

Connection health and index maintenance are independent. If Atlas ping succeeds but an existing index needs maintenance, the application stays online and retries that maintenance in the background instead of incorrectly returning `503` for every route.

The application cannot bypass an Atlas/firewall/VPN network block. For an Atlas TLS handshake error, confirm:

1. Atlas **Network Access** contains your current public IP.
2. The `mongodb+srv://` URI is the current Drivers connection string.
3. Your database username/password are correct and special password characters are URL-encoded.
4. Windows date/time is automatic and correct.
5. VPN, antivirus HTTPS inspection, school/office firewall, or ISP filtering is not blocking outbound MongoDB traffic on port 27017.
6. `certifi`, `pymongo`, and `dnspython` are installed from this project's requirements.

Do not disable TLS certificate verification. If one network blocks Atlas, test once using a trusted mobile hotspot; this identifies an external network filter without weakening security.

## Answer audio

Each AI response has its own speaker button. Click it to read that answer; click again to stop. Long answers are split into safe speech chunks to prevent browser speech from hanging. Tamil and Hindi scripts are detected automatically, and the browser uses an installed matching voice when available. Speech synthesis runs locally in the browser and no generated audio is uploaded or stored.

## Validation commands

```bat
cd backend
python -m pytest -q
python -m pip check
```

```bat
cd frontend
npm run lint
npm run typecheck
npm run audit:a11y
npm run build
npm run test:e2e
```

## Repository layout

```text
backend/       FastAPI API, retrieval, ingestion, security, and tests
frontend/      Next.js UI and browser tests
ops/           Optional backup and restore scripts
README.md      Local setup and troubleshooting
FINAL_AUDIT.md Verified release gates and external acceptance limits
```

Real `.env` files, credentials, package caches, build caches, and private uploads are intentionally excluded from the release ZIP. Use the included `.env.example` templates.

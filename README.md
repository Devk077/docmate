# DoqToq

**Multi-document AI Discussion Rooms** — upload your PDFs, papers, or notes and watch them talk to each other.

Each document gets its own AI-generated persona and responds from its own knowledge. Ask a question and every document in the room answers in its own voice. Use `@mentions` to address a specific document directly.

---

## Architecture

```
Browser (React + Vite)
        │
        │ REST / SSE
        ▼
FastAPI (port 8000)
        │
   ┌────┴──────────┐
   │               │
PostgreSQL      Qdrant
(rooms, docs,  (vector search
 sessions,      per document)
 history)
        │
   LLM Provider
 (Gemini / Mistral / Ollama)
```

---

## Quick Start

### Prerequisites

| Tool | Required for |
|---|---|
| Python 3.10+ | Backend |
| Node.js 18+ | Frontend |
| Docker Desktop | Qdrant (vector DB) |
| PostgreSQL 14+ | Room & chat storage |

### 1. Clone & configure

```bash
git clone https://github.com/your-username/doqtoq.git
cd doqtoq

cp .env.example .env
# Edit .env — add your GOOGLE_API_KEY and DATABASE_URL at minimum
```

### 2. Set up PostgreSQL

Create the database and run the schema (see `dev_docs/groups_database_schema.md`):

```bash
psql -U postgres -c "CREATE DATABASE doqtoq;"
psql -U postgres -d doqtoq -f dev_docs/schema.sql   # if the SQL file exists
```

### 3. Set up the Python environment

```bash
python -m venv venv

# Linux / Mac
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 4. Start everything

**Linux / Mac:**
```bash
chmod +x start_doqtoq.sh
./start_doqtoq.sh
```

**Windows (PowerShell — run each in a separate terminal):**
```powershell
# Terminal 1 — Qdrant
docker compose up -d qdrant

# Terminal 2 — Backend
$env:PYTHONIOENCODING="utf-8"
venv\Scripts\uvicorn api.main:app --reload --port 8000

# Terminal 3 — Frontend
cd frontend
npm install   # first time only
npm run dev
```

### 5. Open the app

| Service | URL |
|---|---|
| React UI | http://localhost:5173 |
| FastAPI + Swagger | http://localhost:8000/docs |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Project Structure

```
doqtoq/
├── api/                  # FastAPI routes (rooms, documents, chat)
├── backend/              # RAG engine, LLM wrappers, DB helpers, prompts
│   ├── db/               # PostgreSQL CRUD helpers
│   ├── prompts/          # System prompt & persona generation
│   └── vectorstore/      # Qdrant indexing & retrieval
├── frontend/             # React + Vite + TypeScript UI
│   └── src/
│       ├── api/          # Typed API client
│       ├── components/   # UI components
│       ├── hooks/        # Custom React hooks
│       ├── pages/        # Home & Room pages
│       └── styles/       # CSS modules
├── dev_docs/             # Database schema, implementation notes
├── data/                 # Runtime data — gitignored
│   ├── uploads/          # Uploaded documents
│   └── vectorstore/      # Qdrant local storage
├── docker-compose.yml    # Qdrant container
├── requirements.txt      # Python dependencies
├── start_doqtoq.sh       # One-command startup (Linux/Mac)
└── .env.example          # Environment variable template
```

---

## Environment Variables

See `.env.example` for the full reference. Key variables:

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Gemini API key |
| `MISTRAL_API_KEY` | Mistral API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `QDRANT_URL` | Qdrant server URL (default `http://localhost:6333`) |
| `FRONTEND_URL` | React origin for CORS (default `http://localhost:5173`) |

---

## Features

- **Multi-voice discussions** — each uploaded document responds as its own AI persona
- **`@mention` routing** — address a specific document; it answers first
- **Session history** — chat history is persisted per session in PostgreSQL
- **Document management** — add or remove documents mid-conversation
- **Per-document settings** — tune temperature, top-K, model per document via the 3-dot menu
- **PDF preview** — click any document card to preview it inline
- **Streaming responses** — real-time SSE output as documents "think"
- **Multiple LLM backends** — Google Gemini, Mistral, Ollama (local)

---

## Development

```bash
# Run backend only (with hot-reload)
venv\Scripts\uvicorn api.main:app --reload --port 8000   # Windows
source venv/bin/activate && uvicorn api.main:app --reload --port 8000  # Linux/Mac

# Run frontend only
cd frontend && npm run dev

# Type-check frontend
cd frontend && npx tsc --noEmit
```

---

## License

MIT

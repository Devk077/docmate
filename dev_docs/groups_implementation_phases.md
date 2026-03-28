# DoqToq Groups — Phased Implementation Plan

*This is the master execution document. Work through phases in order. Do not start a phase until the previous one is fully delivered and tested.*

---

## Architectural Decisions (Locked)

| # | Decision | Resolution |
|---|---|---|
| 1 | Routing LLM | Use the **user-selected room model** for routing and compaction |
| 2 | ChromaDB support | **Both Qdrant and ChromaDB** supported via parallel collection naming |
| 3 | Final synthesis | **No Orchestrator summary** — individual document responses stand alone |
| 4 | `@mention` routing | Typing `@PersonaName` routes exclusively to that doc + **autocomplete in UI** |
| 5 | **Frontend stack** | **React + Vite + TypeScript** (migrated from Streamlit) |
| 6 | **API layer** | **FastAPI** with SSE streaming (replaces Streamlit session state) |

---

## Phase Overview

| Phase | Name | Focus | Status |
|---|---|---|---|
| **1** | Database Foundation | PostgreSQL schema, connection layer, migrations | ✅ Done |
| **2** | Vector Store Upgrade | Dynamic collection names per document, both Qdrant and Chroma | ✅ Done |
| **3** | Orchestrator Backend | Core GroupOrchestrator, routing, compaction, web search | ✅ Done |
| **4** | Prompts & Persona | Group-mode prompts, persona name generation | ✅ Done |
| **5** | ~~Frontend — Room UI~~ | ~~Streamlit rooms list, create room, participants panel~~ | 🔄 Replaced by 5R |
| **5R** | FastAPI Backend Layer | REST + SSE API wrapping the GroupOrchestrator | 🔲 Next |
| **6R** | React Frontend | Full Discord-style React UI with streaming chat | 🔲 Upcoming |
| **7R** | Integration & Polish | End-to-end wiring, session restore, edge cases | 🔲 Upcoming |
| **8** | Testing & Documentation | Full test suite, update all docs | 🔲 Upcoming |

---

## Phase 1 — Database Foundation ✅

### Goal
Establish persistent relational storage (PostgreSQL) for rooms, documents, sessions, chat history, context summaries, and web search logs. Nothing in the app will work in groups mode without this layer.

### What AI Does
- Write `backend/db/schema.sql` with all 6 tables:
  - `rooms`, `documents`, `chat_sessions`, `chat_messages`, `context_summaries`, `web_search_logs`
- Write `backend/db/__init__.py` (package init)
- Write `backend/db/postgres.py` with:
  - `get_connection()` factory using `DATABASE_URL` env var
  - CRUD helpers: `create_room()`, `get_room()`, `add_document()`, `get_documents_in_room()`, `save_message()`, `get_session_messages()`, `save_context_summary()`, `get_latest_summary()`, `log_web_search()`
- Update `.env.example` with `DATABASE_URL=postgresql://user:password@localhost:5432/doqtoq`

### What Human Does
- **Install PostgreSQL** locally (or use Docker: `docker run --name doqtoq-pg -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres`)
- **Create the database**: `createdb doqtoq` (or via pgAdmin)
- **Run the schema**: `psql -d doqtoq -f backend/db/schema.sql`
- **Set** `DATABASE_URL` in `.env`

### Deliverables
- [x] `backend/db/schema.sql` — all 6 CREATE TABLE statements
- [x] `backend/db/postgres.py` — all CRUD functions
- [x] `.env.example` updated with `DATABASE_URL`
- [x] Human confirms DB is up and schema is applied

---

## Phase 2 — Vector Store Upgrade ✅

### Goal
Make the vectorstore layer support **dynamic collection names** per document (e.g., `dtq_{room_id}_{slug}`). This is required for isolating each document's embeddings in a shared Qdrant/Chroma instance.

### What AI Does
- Modify `backend/vectorstore/config.py`:
  - Add optional `collection_name_override: str = None` field to `QdrantConfig` and `ChromaConfig`
- Modify `backend/vectorstore/factory.py`:
  - `get_vector_database(embedding_model, collection_name=None, clear_existing=False)` — if `collection_name` is provided, uses it instead of the env-configured default
- Modify `backend/vectorstore/qdrant_db.py`:
  - Accept and use dynamic `collection_name` at init
- Modify `backend/vectorstore/chroma_db.py`:
  - Accept and use dynamic `collection_name` at init
- Write a helper `backend/vectorstore/naming.py`:
  - `make_collection_name(room_id: str, filename: str) -> str` — generates `dtq_{room_id}_{slug}` (safe, lowercase, no special chars)
  - `delete_collection(collection_name: str)` — removes a collection when a doc is removed from a room

### Deliverables
- [x] `get_vector_database()` accepts `collection_name` override
- [x] Both `QdrantVectorDB` and `ChromaVectorDB` use dynamic names
- [x] `naming.py` helper with `make_collection_name()` and `delete_collection()`

---

## Phase 3 — Orchestrator Backend ✅

### Goal
Write the core `GroupOrchestrator` class that manages a pool of `DocumentRAG` instances, implements the vector gating, sequential speaking, diminishing returns halting, milestone compaction, and silent web search.

### What AI Does
- Write `backend/group_rag_engine.py` → `GroupOrchestrator` class with all routing, streaming, compaction
- Write `backend/web_search_tool.py` — search wrapper + token interceptor

### Deliverables
- [x] `backend/group_rag_engine.py` — `GroupOrchestrator` fully implemented
- [x] `backend/web_search_tool.py` — search wrapper + token interceptor

---

## Phase 4 — Prompts & Persona ✅

### Goal
Replace the single-document prompts with group-aware prompt templates and implement automatic persona name generation on document upload.

### What AI Does
- Write `backend/prompts/group_prompts.py` — persona name generation + group system prompt
- Write `backend/prompts/group_system_prompt.md` — the raw system prompt template

### Deliverables
- [x] `backend/prompts/group_prompts.py` — all prompt functions
- [x] `backend/prompts/group_system_prompt.md` — raw prompt template

---

## Phase 5R — FastAPI Backend Layer 🔲

### Goal
Expose the `GroupOrchestrator` through a clean REST + SSE API. This replaces `app/` entirely. The Streamlit frontend is **retired** after this phase.

### What AI Does

#### New: `api/main.py`
FastAPI application with CORS, lifespan, and router mounts.

#### New: `api/orchestrator_store.py`
Module-level `_store: Dict[str, GroupOrchestrator]` — loaded on first request, cached for the process lifetime. Replaces `st.session_state`.

#### New: `api/routes/rooms.py`
```
GET    /api/rooms              → list all rooms from PostgreSQL
POST   /api/rooms              → create room: name, model_provider
DELETE /api/rooms/{id}         → delete room + Qdrant collections
GET    /api/rooms/{id}/participants → persona list for sidebar
```

#### New: `api/routes/documents.py`
```
POST   /api/rooms/{id}/documents   → upload + chunk + embed + persona name
DELETE /api/rooms/{id}/documents/{doc_id} → remove doc + delete collection
```

#### New: `api/routes/chat.py`
```
POST   /api/rooms/{id}/sessions    → get or create active session
POST   /api/rooms/{id}/chat        → SSE stream from orchestrator.run_round()
```

SSE chunk format:
```json
{"speaker": "The Climate Report", "chunk": "token", "done": false}
{"speaker": "The Climate Report", "chunk": "", "done": true}
{"event": "round_complete"}
```

#### Updated: `.env.example`
Add `API_PORT=8000`, `FRONTEND_URL=http://localhost:5173`

### What Human Does
- `pip install fastapi uvicorn[standard] python-multipart`
- Start API: `uvicorn api.main:app --reload --port 8000`
- Test: `curl http://localhost:8000/api/rooms`

### Deliverables
- [ ] All 6 REST endpoints respond correctly
- [ ] SSE stream returns per-token chunks for a question
- [ ] File upload endpoint saves, indexes, and returns persona name
- [ ] Human confirms with curl/Postman

---

## Phase 6R — React Frontend 🔲

### Goal
Build a premium, Discord-style React frontend that consumes the FastAPI. The UI should **wow** — dark mode, animated streaming, coloured persona bubbles, polished sidebar.

### Tech Stack
- **Vite + React 18 + TypeScript**
- **React Router v6** (SPA with `/` and `/rooms/:id` routes)
- **Custom CSS** (CSS variables, no Tailwind) — full control over aesthetics
- **EventSource API** for SSE streaming

### What AI Does

#### Frontend structure:
```
frontend/
  src/
    api/client.ts            ← typed fetch wrappers
    hooks/
      useSSEStream.ts        ← SSE consumer hook
      useRooms.ts
      useParticipants.ts
    components/
      Sidebar.tsx            ← rooms list + new room button
      NewRoomModal.tsx       ← drag-drop upload + room name form
      RoomView.tsx           ← two-column chat layout
      ParticipantsPanel.tsx  ← live persona status cards
      ChatMessage.tsx        ← coloured bubble (per speaker)
      ChatInput.tsx          ← input + @mention autocomplete
      TypingIndicator.tsx    ← "X is thinking..." animation
    styles/
      globals.css            ← CSS vars, dark theme tokens
      sidebar.css, chat.css, room.css, modal.css
    pages/
      Home.tsx               ← rooms grid with "New Room" CTA
      Room.tsx               ← full discussion room
    App.tsx
    main.tsx
```

#### Key Design Details:
- **Colour palette:** `#0f1117` base, `#1a1d27` surface, `#6c63ff` primary, per-doc accent palette
- **Sidebar:** Collapsible, rooms listed as cards with active glow, hover delete
- **Chat bubbles:** Rounded, speaker name + colour dot top-left, smooth fade-in per token
- **@mention autocomplete:** Floating popover, fuzzy search, keyboard navigable
- **Participants panel:** Avatar-style cards with animated status ring (pulsing = thinking)
- **New Room modal:** Multi-file drag-drop zone, shows file previews + persona names after upload

### What Human Does
- `cd frontend && npm install && npm run dev`
- Open `http://localhost:5173`
- Smoke test: create room → upload → chat → see streaming

### Deliverables
- [ ] Home page shows rooms list with "New Room" button
- [ ] New Room modal opens, accepts files, shows progress
- [ ] Room view: two-column layout, participants panel populated
- [ ] Chat input with @mention autocomplete
- [ ] Streaming tokens appear word-by-word, no flicker
- [ ] Persona bubbles have distinct colours
- [ ] Typing indicator shows per active doc

---

## Phase 7R — Integration & Polish 🔲

### Goal
Wire everything end-to-end, handle edge cases, restore sessions, and polish interactions.

### What AI Does
- Session restore: on room open, load last session messages from PostgreSQL and render them
- Mid-session doc add/remove: REST call → update participants panel live (no page reload)
- Edge cases: 1-doc room, no doc clears gate, LLM error mid-stream, Qdrant unreachable
- Loading skeletons: show while rooms/messages are fetching
- Error toasts: friendly messages for API failures
- Mobile-responsive layout

### What Human Does
- Full end-to-end smoke test
- Report any remaining bugs

### Deliverables
- [ ] Session history restores on room open
- [ ] Adding/removing docs live-updates participants panel
- [ ] All error cases show friendly UI feedback
- [ ] App works on a mobile viewport

---

## Phase 8 — Testing & Documentation 🔲

### Goal
Write automated tests for critical backend components and update all developer documentation.

### What AI Does
- `tests/test_group_rag_engine.py` — routing gate, diminishing returns, compaction
- `tests/test_api_rooms.py` — API endpoint tests (FastAPI TestClient)
- `tests/test_web_search_tool.py` — token interception
- `tests/test_postgres.py` — CRUD helpers
- Update `.env.example` with all env vars
- Write `dev_docs/groups_implementation_summary.md`

### What Human Does
- `pytest tests/`
- Final review before marking feature complete

### Deliverables
- [ ] All tests pass
- [ ] Docs fully updated

---

## New Run Commands (after Phase 5R)

```bash
# Terminal 1 — Python API
uvicorn api.main:app --reload --port 8000

# Terminal 2 — React dev server
cd frontend && npm run dev

# Open: http://localhost:5173
```

---

## Dependency Order

```
Phase 1 (DB) ✅
  └─► Phase 2 (Vector Store) ✅
        └─► Phase 3 (Orchestrator) ✅
              └─► Phase 4 (Prompts) ✅
                    └─► Phase 5R (FastAPI API layer)
                          └─► Phase 6R (React UI)
                                └─► Phase 7R (Integration)
                                      └─► Phase 8 (Testing)
```

> Phases 1-4 are complete and production-ready. The React migration builds a clean API surface on top of them — no AI logic changes required.


---

## Architectural Decisions (Locked)

| # | Decision | Resolution |
|---|---|---|
| 1 | Routing LLM | Use the **user-selected room model** for routing and compaction |
| 2 | ChromaDB support | **Both Qdrant and ChromaDB** supported via parallel collection naming |
| 3 | Final synthesis | **No Orchestrator summary** — individual document responses stand alone |
| 4 | `@mention` routing | Typing `@PersonaName` routes exclusively to that doc + **autocomplete in UI** |

---

## Phase Overview

| Phase | Name | Focus |
|---|---|---|
| **1** | Database Foundation | PostgreSQL schema, connection layer, migrations |
| **2** | Vector Store Upgrade | Dynamic collection names per document, both Qdrant and Chroma |
| **3** | Orchestrator Backend | Core GroupOrchestrator, routing, compaction, web search |
| **4** | Prompts & Persona | Group-mode prompts, persona name generation |
| **5** | Frontend — Room UI | Rooms list, create room, participants panel, layout switch |
| **6** | Frontend — Chat & Streaming | Multi-speaker chat bubbles, `@mention` autocomplete, multi-stream queue |
| **7** | Integration & Polish | End-to-end wiring, error handling, edge cases |
| **8** | Testing & Documentation | Full test suite, update all docs |

---

## Phase 1 — Database Foundation

### Goal
Establish persistent relational storage (PostgreSQL) for rooms, documents, sessions, chat history, context summaries, and web search logs. Nothing in the app will work in groups mode without this layer.

### What AI Does
- Write `backend/db/schema.sql` with all 6 tables:
  - `rooms`, `documents`, `chat_sessions`, `chat_messages`, `context_summaries`, `web_search_logs`
- Write `backend/db/__init__.py` (package init)
- Write `backend/db/postgres.py` with:
  - `get_connection()` factory using `DATABASE_URL` env var
  - CRUD helpers: `create_room()`, `get_room()`, `add_document()`, `get_documents_in_room()`, `save_message()`, `get_session_messages()`, `save_context_summary()`, `get_latest_summary()`, `log_web_search()`
- Update `.env.example` with `DATABASE_URL=postgresql://user:password@localhost:5432/doqtoq`

### What Human Does
- **Install PostgreSQL** locally (or use Docker: `docker run --name doqtoq-pg -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres`)
- **Create the database**: `createdb doqtoq` (or via pgAdmin)
- **Run the schema**: `psql -d doqtoq -f backend/db/schema.sql`
- **Set** `DATABASE_URL` in `.env`

### Deliverables
- [ ] `backend/db/schema.sql` — all 6 CREATE TABLE statements
- [ ] `backend/db/postgres.py` — all CRUD functions
- [ ] `.env.example` updated with `DATABASE_URL`
- [ ] Human confirms DB is up and schema is applied

---

## Phase 2 — Vector Store Upgrade

### Goal
Make the vectorstore layer support **dynamic collection names** per document (e.g., `dtq_{room_id}_{slug}`). This is required for isolating each document's embeddings in a shared Qdrant/Chroma instance.

### What AI Does
- Modify `backend/vectorstore/config.py`:
  - Add optional `collection_name_override: str = None` field to `QdrantConfig` and `ChromaConfig`
- Modify `backend/vectorstore/factory.py`:
  - `get_vector_database(embedding_model, collection_name=None, clear_existing=False)` — if `collection_name` is provided, uses it instead of the env-configured default
- Modify `backend/vectorstore/qdrant_db.py`:
  - Accept and use dynamic `collection_name` at init
- Modify `backend/vectorstore/chroma_db.py`:
  - Accept and use dynamic `collection_name` at init
- Write a helper `backend/vectorstore/naming.py`:
  - `make_collection_name(room_id: str, filename: str) -> str` — generates `dtq_{room_id}_{slug}` (safe, lowercase, no special chars)
  - `delete_collection(collection_name: str)` — removes a collection when a doc is removed from a room

### What Human Does
- Test that collections work independently:
  - Run app with two different collection names, upload different docs to each, verify retrieval only returns the right doc's content

### Deliverables
- [ ] `get_vector_database()` accepts `collection_name` override
- [ ] Both `QdrantVectorDB` and `ChromaVectorDB` use dynamic names
- [ ] `naming.py` helper with `make_collection_name()` and `delete_collection()`
- [ ] Human confirms isolation test: two separate collections return separate results

---

## Phase 3 — Orchestrator Backend

### Goal
Write the core `GroupOrchestrator` class that manages a pool of `DocumentRAG` instances, implements the vector gating, sequential speaking, diminishing returns halting, milestone compaction, and silent web search.

### What AI Does
- Write `backend/group_rag_engine.py` → `GroupOrchestrator` class:
  - `__init__(room_id, model_provider, embedding_provider, embedding_model)` — loads docs from PostgreSQL, creates one `DocumentRAG` per doc using dynamic collection names
  - `add_document(file_path, persona_name, collection_name)` — registers a new doc at runtime
  - `route(question)` → `List[DocumentRAG]` — runs the **vector similarity gate** (`GROUP_SIMILARITY_THRESHOLD=0.65`) against each doc's collection, returns ordered list of qualifying speakers
  - `parse_mention(message)` → `DocumentRAG | None` — extracts `@PersonaName` from user message, bypasses vector gate
  - `run_round(question)` → `Iterator[Dict]` — the main coroutine: iterates through speaking queue, yields streamed chunks per doc, applies **diminishing returns** check (`GROUP_DIMINISHING_RETURNS_SIM=0.92`) to mark docs "spent"
  - `compact_history(session_id)` — compacts oldest message batch into PostgreSQL `context_summaries` table when `turn_count % GROUP_DOC_COMPACTION_N == 0`
  - `build_context_for_llm(session_id)` → `str` — returns `[latest_summary] + [last N raw messages]` ready for injection into prompt
- Write `backend/web_search_tool.py`:
  - `run_search(query: str) -> str` — wrapper around DuckDuckGo search via `langchain_community.tools`
  - `intercept_search_request(stream_chunk: str) -> Tuple[bool, str]` — checks if chunk contains `[WEB_SEARCH_REQUEST: ...]` token
  - Logs search to `web_search_logs` in PostgreSQL

### What Human Does
- Install new dependencies: `pip install langchain-community duckduckgo-search asyncpg psycopg2-binary`
- Test routing manually:
  - Create 2 `DocumentRAG` instances pointing to very different documents
  - Run `orchestrator.route("some question")` and verify only the relevant doc clears the gate
- Test compaction: artificially set `GROUP_DOC_COMPACTION_N=2` in `.env` and verify summary table gets rows after 2 messages

### Deliverables
- [ ] `backend/group_rag_engine.py` — `GroupOrchestrator` fully implemented
- [ ] `backend/web_search_tool.py` — search wrapper + token interceptor
- [ ] Routing and compaction verified manually
- [ ] New env vars documented in `.env.example`

---

## Phase 4 — Prompts & Persona

### Goal
Replace the single-document prompts with group-aware prompt templates and implement automatic persona name generation on document upload.

### What AI Does
- Write `backend/prompts/group_prompts.py`:
  - `generate_persona_name(file_path, model_provider) -> str` — makes a short LLM call with the document's first 500 characters and returns a friendly name, e.g. *"The Climate Report"*
  - `load_group_system_prompt(persona_name, all_personas) -> str` — group-mode system prompt; the doc knows its name, knows other docs exist, can use `@mentions`, can emit `[WEB_SEARCH_REQUEST: ...]`
  - `load_group_contribution_check_prompt() -> str` — short prompt asking doc: "Does this question relate to your content? Yes/No."
  - `load_compaction_prompt() -> str` — prompt for summarizing a batch of messages
- Write `backend/prompts/group_system_prompt.md` — the raw system prompt template

### What Human Does
- Upload 3 test documents and verify that each gets a distinct, sensible persona name
- Confirm group system prompt correctly names the doc, lists its peers, and includes instructions for `@mentions`

### Deliverables
- [ ] `backend/prompts/group_prompts.py` — all 4 prompt functions
- [ ] `backend/prompts/group_system_prompt.md` — raw prompt template
- [ ] Human confirms persona names are sensible for varied document types

---

## Phase 5 — Frontend: Room UI

### Goal
Replace the single-document centered layout with a Discord-style multi-room interface. Rooms are listed in the sidebar, and the active room shows a two-column chat + participants layout.

### What AI Does
- Modify `app/main.py`:
  - Change `layout="centered"` → `layout="wide"`
  - Replace single file uploader + `qa_chain` block with room-based routing logic
  - If no room is selected → show **Home Screen** (rooms list + "New Room" button)
  - If room is selected → show **Room View** (chat panel + participants panel)
- Modify `app/sidebar.py`:
  - Add **Rooms List** section: reads rooms from PostgreSQL, renders each as a button
  - Add **"+ New Room"** button that triggers a modal/form
- Write `app/room_manager.py` (new):
  - `render_new_room_form()` — multi-file uploader + room name input + "Start Discussion" button
  - `create_room(name, files)` → `room_id` — saves room to DB, uploads docs, generates persona names, creates vector collections
  - `load_room(room_id)` → `GroupOrchestrator` — restores orchestrator from DB
- Modify `app/styles.py`:
  - Two-column layout CSS
  - Participant card styling (green ● active dot, grey ○ idle dot)
  - Room list item hover styles
  - Orchestrator status badge

### What Human Does
- Verify UI: create a room, name it, upload 2 files, click "Start Discussion"
- Confirm participants panel shows both docs with persona names
- Confirm sidebar shows the new room and clicking it navigates back

### Deliverables
- [ ] Home screen with rooms list works
- [ ] New Room form saves to DB and creates vector collections
- [ ] Two-column Room View renders with participants panel
- [ ] Sidebar navigation between rooms works

---

## Phase 6 — Frontend: Chat & Streaming

### Goal
Implement multi-speaker streaming chat with `@mention` autocomplete, distinct persona bubbles, and the Orchestrator status indicator.

### What AI Does
- Modify `app/chat.py`:
  - Replace single `qa_chain.query_stream()` call with `orchestrator.run_round(question)`
  - Render chat history with `("document", persona_name, msg)` tuples — each doc gets its bubble with `sender_name` label
  - Render Orchestrator status inline: *"Routing..."*, *"The Climate Report is thinking..."*
  - Parse `@mention` from user input and pass to `orchestrator.parse_mention()`
- Modify `app/streaming_queue.py`:
  - Add `handle_multi_stream(stream_sources: List[Iterator]) -> Iterator` — chains multiple doc streams sequentially without triggering Streamlit rerun
- Implement `@mention` autocomplete:
  - When user types `@` in the chat input, show a suggestion list of all `persona_name` values in the current room
  - Selecting a suggestion inserts `@PersonaName ` into the input
  - *Note: Streamlit's native `st.chat_input` doesn't support autocomplete natively; this will be implemented using a custom `st.text_input` + `st.selectbox` combo or JavaScript injection via `st.components.v1.html`*
- Modify `app/styles.py`:
  - Per-doc bubble colour coding (first 6 docs get distinct colours from a palette)
  - `@mention` text highlighted in input

### What Human Does
- Test full conversation flow:
  1. Upload 2 docs, ask a general question → both should reply sequentially
  2. Type `@` → autocomplete list should appear
  3. Use `@mention` to target one doc → only that doc replies
  4. Ask multiple questions to verify history is maintained correctly

### Deliverables
- [ ] Multi-speaker chat bubbles with persona names render
- [ ] `@mention` autocomplete works in chat input
- [ ] Orchestrator status indicator shows correct state
- [ ] Sequential streaming of multiple docs works without page flicker

---

## Phase 7 — Integration & Polish

### Goal
Wire all phases together into a working end-to-end product, fix integration bugs, handle edge cases, and improve robustness.

### What AI Does
- Handle edge cases:
  - Room with 1 doc → behaves like original single-doc chat (no group logic)
  - No doc clears the similarity gate → fallback to highest-scoring doc; if score is very low, Orchestrator tells user
  - Web search token intercepted mid-stream → pause doc, run other docs, resume
  - User adds a new doc to an existing room mid-chat → generate persona, create collection, add to participants panel live
  - User removes a doc → delete its Qdrant/Chroma collection, remove from PostgreSQL
- Session resume: when user returns to a room, load last session's messages from PostgreSQL and render in chat
- Error handling: DB down, Qdrant unreachable, LLM API error — graceful degradation with user-facing messages
- Update `app/config.py` with all new session state keys

### What Human Does
- Full end-to-end smoke test:
  - Create room → upload 3 docs → ask 5 questions → leave room → come back → verify history restored
  - Add a 4th doc mid-session → verify it joins the participants panel
  - Remove a doc → verify it disappears
  - Force a web search (ask about live news) → verify it is silent to user but logged in DB
- Report any bugs

### Deliverables
- [ ] Resume from previous session works
- [ ] Adding/removing docs from active room works
- [ ] All edge cases handled gracefully
- [ ] No crashes during standard usage flow

---

## Phase 8 — Testing & Documentation

### Goal
Write automated tests for critical backend components and update all developer documentation.

### What AI Does
- Write tests in `tests/`:
  - `test_group_rag_engine.py` — routing gate, diminishing returns, compaction trigger
  - `test_web_search_tool.py` — token interception, search invocation
  - `test_postgres.py` — CRUD helpers (using a test DB)
  - `test_naming.py` — collection name generation and sanitisation
- Update `dev_docs/README.md` to reference new phase docs
- Update `.env.example` with all new Group env vars:
  ```env
  DATABASE_URL=postgresql://user:password@localhost:5432/doqtoq
  GROUP_SIMILARITY_THRESHOLD=0.65
  GROUP_DOC_COMPACTION_N=10
  GROUP_DIMINISHING_RETURNS_SIM=0.92
  GROUP_MAX_ROOM_DOCS=10
  ```
- Write `dev_docs/groups_implementation_summary.md` — post-implementation summary of what was built and what changed in each file

### What Human Does
- Run the test suite: `pytest tests/`
- Review and approve all documentation
- Final review of the running app before marking the feature complete

### Deliverables
- [ ] All new tests pass
- [ ] `.env.example` fully updated
- [ ] `dev_docs/README.md` updated
- [ ] `dev_docs/groups_implementation_summary.md` written
- [ ] Feature marked complete ✅

---

## Dependency Order

```
Phase 1 (DB)
  └─► Phase 2 (Vector Store)
        └─► Phase 3 (Orchestrator Backend)
              └─► Phase 4 (Prompts & Persona)
                    ├─► Phase 5 (Room UI)
                    │     └─► Phase 6 (Chat & Streaming)
                    │           └─► Phase 7 (Integration)
                    │                 └─► Phase 8 (Testing)
                    └─► (feeds into Phase 3)
```

> Phases 3 and 4 are partially interdependent — persona generation (Phase 4) is needed by the Orchestrator (Phase 3) at the point when a document is first added to a room. Start Phase 3 first, stub the persona function, then replace with the real implementation in Phase 4.

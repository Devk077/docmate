# DoqToq Groups — Developer Documentation Index

*Reference this file first when starting development on the DoqToq Groups feature.*

---

## What is DoqToq Groups?
An upgrade to the DoqToq platform that allows multiple documents to participate in a shared group discussion. The system is document-count agnostic — one doc behaves like the current single-doc chat, multiple docs activate group discussion automatically.

---

## Documentation Files

| File | What's inside |
|------|--------------|
| [`project_overview.md`](./project_overview.md) | High-level overview of the DoqToq codebase and existing architecture |
| [`doqtoq_groups_architecture.md`](./doqtoq_groups_architecture.md) | Early architectural analysis — how we go from single-doc to multi-doc |
| [`groups_qna_decision_log.md`](./groups_qna_decision_log.md) | **All design decisions** — read this before writing any code |
| [`groups_database_schema.md`](./groups_database_schema.md) | PostgreSQL schema — all 6 tables with SQL, ER diagram, and usage patterns |
| [`groups_ui_user_journey.md`](./groups_ui_user_journey.md) | Discord-inspired UI design and step-by-step user journey |

---

## Key Concepts (Quick Reference)

| Concept | Summary |
|---------|---------|
| **Discussion Room** | A persistent space where a user uploads docs and chats with them as a group |
| **Orchestrator** | The AI that manages turn-taking, routing, loop prevention, and web search |
| **Vector Gating** | Routing method — similarity search decides which docs speak (no extra LLM calls) |
| **Mutex** | Only one document generates at a time; others wait their turn |
| **Diminishing Returns** | If a doc's response is too similar to the previous, it's marked "spent" for that round |
| **Milestone Compaction** | Chat history is summarized every N messages to keep LLM context clean and cheap |
| **Silent Web Search** | Orchestrator searches the web on a doc's behalf; no visible UI notification; fully logged |
| **Persona Name** | A friendly name auto-generated per document on upload, stored in PostgreSQL, reused forever |

---

## Environment Variables (Groups-specific)

```env
GROUP_SIMILARITY_THRESHOLD=0.65       # Min score for a doc to enter speaking queue
GROUP_DOC_COMPACTION_N=10             # Message milestone to trigger compaction
GROUP_DIMINISHING_RETURNS_SIM=0.92    # Similarity above which a doc is marked spent
GROUP_MAX_ROOM_DOCS=10                # Max documents per room
DATABASE_URL=postgresql://...         # PostgreSQL connection string
```

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `backend/group_rag_engine.py` | NEW — core Orchestrator logic |
| `backend/web_search_tool.py` | NEW — Orchestrator-owned web search wrapper |
| `backend/prompts/group_prompts.py` | NEW — group-mode prompt templates |
| `backend/db/postgres.py` | NEW — PostgreSQL connection helpers |
| `backend/db/schema.sql` | NEW — all CREATE TABLE definitions |
| `backend/vectorstore/config.py` | MODIFY — dynamic collection names |
| `app/chat.py` | MODIFY — multi-speaker rendering |
| `app/uploader.py` | MODIFY — multi-file upload + persona generation |
| `app/sidebar.py` | MODIFY — room management + mid-chat model switcher |
| `app/streaming_queue.py` | MODIFY — sequential multi-source streams |
| `.env.example` | MODIFY — add group vars + DATABASE_URL |

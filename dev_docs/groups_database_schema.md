# DoqToq Groups — PostgreSQL Database Schema

*Why PostgreSQL? Document metadata, persona names, chat history, and web search logs are relational data — they have clear relationships between entities (a room has documents, a session has messages). Qdrant stores the vector embeddings; PostgreSQL stores everything else. This avoids re-generating persona names on every session and allows rooms/history to be persisted and resumed.*

---

## Schema Design

### Table: `rooms`
Represents a Discussion Room created by the user.
```sql
CREATE TABLE rooms (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,              -- user-given room name
    ai_model     TEXT DEFAULT 'google',      -- default model (can be changed mid-chat)
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
```

---

### Table: `documents`
Each document uploaded to a room. The persona name is generated **once on upload and stored here** — no re-generation on subsequent sessions.
```sql
CREATE TABLE documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id             UUID REFERENCES rooms(id) ON DELETE CASCADE,
    filename            TEXT NOT NULL,          -- original filename
    persona_name        TEXT NOT NULL,          -- auto-generated, e.g. "The Climate Report"
    qdrant_collection   TEXT NOT NULL UNIQUE,   -- e.g. dtq_{room_id}_{slug}
    file_path           TEXT,                   -- path on disk (in data/uploads/)
    added_at            TIMESTAMP DEFAULT NOW()
);
```

---

### Table: `chat_sessions`
A single conversation run within a room. A room can have multiple sessions over time (user can leave and resume).
```sql
CREATE TABLE chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id     UUID REFERENCES rooms(id) ON DELETE CASCADE,
    ai_model    TEXT,           -- model at session start (recorded per session)
    started_at  TIMESTAMP DEFAULT NOW(),
    ended_at    TIMESTAMP       -- NULL while session is active
);
```

---

### Table: `chat_messages`
Every message in a session — user, document, orchestrator (if it needs to inform the user), or system.
```sql
CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,      -- 'user' | 'document' | 'orchestrator' | 'system'
    sender_name     TEXT,               -- persona name (e.g. "The Climate Report") or "You"
    document_id     UUID REFERENCES documents(id), -- which doc, if role='document'
    content         TEXT NOT NULL,      -- full message text
    ai_model_used   TEXT,               -- model that generated this message (can change mid-chat)
    turn_number     INTEGER NOT NULL,   -- ordering within the session
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

### Table: `context_summaries`
Stores the rolling compacted summary for a session. One row per compaction milestone.
```sql
CREATE TABLE context_summaries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    summary             TEXT NOT NULL,      -- append-only compressed summary text
    covers_up_to_turn   INTEGER NOT NULL,   -- which turn number this summary covers up to
    created_at          TIMESTAMP DEFAULT NOW()
);
```

> **How it works:** At every N messages, a new row is inserted with an updated summary that appends the latest batch. When building LLM context, the app reads the most recent `context_summaries` row + the last N `chat_messages` rows.

---

### Table: `web_search_logs`
Logs every web search performed by the Orchestrator, for audit and debugging.
```sql
CREATE TABLE web_search_logs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID REFERENCES chat_sessions(id),
    requesting_document_id  UUID REFERENCES documents(id),
    query                   TEXT NOT NULL,          -- what the doc asked to search for
    result                  TEXT,                   -- what was returned
    searched_at             TIMESTAMP DEFAULT NOW()
);
```

---

## Entity Relationship Diagram

```
rooms
  │
  ├──< documents          (one room has many docs)
  │       │
  │       └── qdrant_collection  (one Qdrant collection per doc)
  │
  └──< chat_sessions      (one room has many sessions over time)
          │
          ├──< chat_messages     (one session has many messages)
          │       └── document_id  (FK to documents, if role='document')
          │
          ├──< context_summaries  (compaction milestones per session)
          └──< web_search_logs    (all web searches in a session)
```

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| Persona name stored in `documents` | Generated once on first upload; never regenerated |
| Qdrant collection name stored in `documents` | Persistent across sessions; allows resuming without re-embedding |
| `ai_model_used` per message | Tracks model changes mid-chat accurately |
| `context_summaries` separate table | Clean retrieval pattern for the hybrid compaction strategy |
| `web_search_logs` separate table | Silent web search needs an audit trail; keeps `chat_messages` clean |
| `turn_number` in `chat_messages` | Enables correct ordering and milestone calculation without relying on timestamps |

---

## Usage Patterns

**Loading a resumed session:**
```sql
-- Get last context summary
SELECT summary, covers_up_to_turn FROM context_summaries
WHERE session_id = $1 ORDER BY covers_up_to_turn DESC LIMIT 1;

-- Get messages since last summary
SELECT role, sender_name, content FROM chat_messages
WHERE session_id = $1 AND turn_number > $last_turn ORDER BY turn_number ASC;
```

**At compaction milestone:**
```sql
-- Insert updated summary
INSERT INTO context_summaries (session_id, summary, covers_up_to_turn)
VALUES ($1, $new_summary, $current_turn);
```

**Logging a web search:**
```sql
INSERT INTO web_search_logs (session_id, requesting_document_id, query, result)
VALUES ($1, $2, $3, $4);
```

-- DoqToq Groups — PostgreSQL Schema
-- Run this file once to initialize the database:
--   psql -d docmate -f backend/db/schema.sql
--
-- All tables use UUIDs as primary keys for easy distributed use.
-- Cascade deletes ensure cleanup is automatic when a room is deleted.

-- Enable UUID generation (required for gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- Table: rooms
-- A Discussion Room created by the user. One room holds
-- multiple documents and multiple sessions over time.
-- ============================================================
CREATE TABLE IF NOT EXISTS rooms (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,                       -- user-given room name
    ai_model    TEXT        NOT NULL DEFAULT 'google',      -- default model for the room
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Table: documents
-- Each document uploaded into a room. Persona name is generated
-- once on upload and stored here permanently — never re-generated.
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id             UUID    NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    filename            TEXT    NOT NULL,           -- original uploaded filename
    persona_name        TEXT    NOT NULL,           -- AI-generated friendly name, e.g. "The Climate Report"
    qdrant_collection   TEXT    NOT NULL UNIQUE,    -- vector DB collection, e.g. dtq_{room_id}_{slug}
    file_path           TEXT,                       -- path on disk: data/uploads/...
    added_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Table: chat_sessions
-- A single conversation run within a room. A room can have
-- multiple sessions (user leaves and comes back).
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id     UUID    NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    ai_model    TEXT,                       -- model in use when this session started
    started_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMP                   -- NULL while session is still active
);

-- ============================================================
-- Table: chat_messages
-- Every message in a session — from user, a document, or
-- the orchestrator (for system-level notifications).
-- role values: 'user' | 'document' | 'orchestrator' | 'system'
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID    NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT    NOT NULL CHECK (role IN ('user', 'document', 'orchestrator', 'system')),
    sender_name     TEXT,                   -- persona name or "You" for user messages
    document_id     UUID    REFERENCES documents(id) ON DELETE SET NULL,  -- which doc, if role='document'
    content         TEXT    NOT NULL,       -- full message text
    ai_model_used   TEXT,                   -- model that generated this message
    turn_number     INTEGER NOT NULL,       -- ordering within the session (1, 2, 3...)
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for fast retrieval of messages in a session in order
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_turn
    ON chat_messages(session_id, turn_number ASC);

-- ============================================================
-- Table: context_summaries
-- Rolling compaction summaries for a session.
-- Every N messages (GROUP_DOC_COMPACTION_N), a new row is
-- inserted containing an updated summary up to that turn.
-- LLM receives: [latest summary row] + [last N raw messages].
-- ============================================================
CREATE TABLE IF NOT EXISTS context_summaries (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID    NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    summary             TEXT    NOT NULL,       -- append-only compacted text
    covers_up_to_turn   INTEGER NOT NULL,       -- turn number this summary is current through
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Table: web_search_logs
-- Audit trail for every silent web search performed by the
-- Orchestrator on behalf of a document mid-discussion.
-- ============================================================
CREATE TABLE IF NOT EXISTS web_search_logs (
    id                      UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID    NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    requesting_document_id  UUID    REFERENCES documents(id) ON DELETE SET NULL,
    query                   TEXT    NOT NULL,   -- what the document searched for
    result                  TEXT,               -- top search result returned
    searched_at             TIMESTAMP NOT NULL DEFAULT NOW()
);

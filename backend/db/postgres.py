"""
DoqToq Groups — PostgreSQL Connection & CRUD Helpers

All database interaction for rooms, documents, sessions, messages,
context summaries, and web search logs lives here.

Requires:
    pip install psycopg2-binary
    DATABASE_URL set in .env, e.g.:
    DATABASE_URL=postgresql://postgres:secret@localhost:5432/docmate
"""

__module_name__ = "db.postgres"

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


# ──────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────

@contextmanager
def get_connection():
    """
    Context manager that yields a psycopg2 connection with
    RealDictCursor (rows returned as dicts) and auto-commits on success.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to your .env file.\n"
            "Example: DATABASE_URL=postgresql://postgres:secret@localhost:5432/docmate"
        )
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
# Rooms
# ──────────────────────────────────────────────────────────────

def create_room(name: str, ai_model: str = "google") -> Dict[str, Any]:
    """
    Create a new Discussion Room.

    Args:
        name: User-given room name.
        ai_model: Default LLM provider for the room ('google', 'mistral', 'ollama').

    Returns:
        The newly created room row as a dict.
    """
    sql = """
        INSERT INTO rooms (name, ai_model)
        VALUES (%s, %s)
        RETURNING *;
    """
    result: Dict[str, Any] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (name, ai_model))
            row = cur.fetchone()
            result = dict(row)
    logger.info(f"{__module_name__} - Created room: {result.get('id')} ({name})")
    return result


def get_all_rooms() -> List[Dict[str, Any]]:
    """
    Retrieve all rooms ordered by most recently updated.

    Returns:
        List of room dicts.
    """
    sql = """
        SELECT r.*, COUNT(d.id)::int AS document_count
        FROM rooms r
        LEFT JOIN documents d ON r.id = d.room_id
        GROUP BY r.id
        ORDER BY r.updated_at DESC;
    """
    rows: List[Dict[str, Any]] = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]
    return rows


def get_room(room_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single room by ID.

    Returns:
        Room dict, or None if not found.
    """
    sql = "SELECT * FROM rooms WHERE id = %s;"
    result: Optional[Dict[str, Any]] = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (room_id,))
            row = cur.fetchone()
            result = dict(row) if row else None
    return result


def update_room_model(room_id: str, ai_model: str) -> None:
    """Update the default AI model for a room (used for mid-chat model switching)."""
    sql = "UPDATE rooms SET ai_model = %s, updated_at = NOW() WHERE id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (ai_model, room_id))


def delete_room(room_id: str) -> None:
    """Delete a room and all its documents/sessions (CASCADE)."""
    sql = "DELETE FROM rooms WHERE id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (room_id,))
    logger.info(f"{__module_name__} - Deleted room: {room_id}")


# ──────────────────────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────────────────────

def add_document(
    room_id: str,
    filename: str,
    persona_name: str,
    qdrant_collection: str,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Register a document in a room after it has been uploaded and embedded.

    Args:
        room_id: UUID of the parent room.
        filename: Original uploaded filename.
        persona_name: AI-generated friendly name (e.g. "The Climate Report").
        qdrant_collection: Vector DB collection name (e.g. dtq_{room_id}_{slug}).
        file_path: Disk path of the uploaded file.

    Returns:
        The newly created document row as a dict.
    """
    sql = """
        INSERT INTO documents (room_id, filename, persona_name, qdrant_collection, file_path)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *;
    """
    result: Dict[str, Any] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (room_id, filename, persona_name, qdrant_collection, file_path))
            row = cur.fetchone()
            result = dict(row)
    logger.info(
        f"{__module_name__} - Added document '{persona_name}' "
        f"(collection={qdrant_collection}) to room {room_id}"
    )
    return result


def get_documents_in_room(room_id: str) -> List[Dict[str, Any]]:
    """
    Get all documents in a room, ordered by upload time.

    Returns:
        List of document dicts.
    """
    sql = "SELECT * FROM documents WHERE room_id = %s ORDER BY added_at ASC;"
    rows: List[Dict[str, Any]] = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (room_id,))
            rows = [dict(r) for r in cur.fetchall()]
    return rows


def get_document_by_id(document_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single document by its UUID."""
    sql = "SELECT * FROM documents WHERE id = %s;"
    result: Optional[Dict[str, Any]] = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (document_id,))
            row = cur.fetchone()
            result = dict(row) if row else None
    return result


def remove_document(document_id: str) -> None:
    """
    Remove a document from a room.
    Note: The caller is responsible for deleting the vector DB collection.
    """
    sql = "DELETE FROM documents WHERE id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (document_id,))
    logger.info(f"{__module_name__} - Removed document: {document_id}")


# ──────────────────────────────────────────────────────────────
# Chat Sessions
# ──────────────────────────────────────────────────────────────

def create_session(room_id: str, ai_model: str) -> Dict[str, Any]:
    """
    Start a new chat session for a room.

    Args:
        room_id: UUID of the room.
        ai_model: Model provider in use at session start.

    Returns:
        The newly created session row as a dict.
    """
    sql = """
        INSERT INTO chat_sessions (room_id, ai_model)
        VALUES (%s, %s)
        RETURNING *;
    """
    result: Dict[str, Any] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (room_id, ai_model))
            row = cur.fetchone()
            result = dict(row)
    logger.info(f"{__module_name__} - Created session: {result.get('id')} for room {room_id}")
    return result


def end_session(session_id: str) -> None:
    """Mark a session as ended by setting ended_at to now."""
    sql = "UPDATE chat_sessions SET ended_at = NOW() WHERE id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id,))


def get_latest_session(room_id: str) -> Optional[Dict[str, Any]]:
    """Get the most recent session for a room (for resuming)."""
    sql = """
        SELECT * FROM chat_sessions
        WHERE room_id = %s
        ORDER BY started_at DESC
        LIMIT 1;
    """
    result: Optional[Dict[str, Any]] = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (room_id,))
            row = cur.fetchone()
            result = dict(row) if row else None
    return result


# ──────────────────────────────────────────────────────────────
# Chat Messages
# ──────────────────────────────────────────────────────────────

def save_message(
    session_id: str,
    role: str,
    content: str,
    turn_number: int,
    sender_name: Optional[str] = None,
    document_id: Optional[str] = None,
    ai_model_used: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save a single message to the chat history.

    Args:
        session_id: UUID of the active session.
        role: 'user' | 'document' | 'orchestrator' | 'system'
        content: Full text of the message.
        turn_number: Sequential turn counter within the session.
        sender_name: Display name (persona name or "You").
        document_id: UUID of the speaking document (if role='document').
        ai_model_used: Which LLM generated this message.

    Returns:
        The saved message row as a dict.
    """
    sql = """
        INSERT INTO chat_messages
            (session_id, role, sender_name, document_id, content, ai_model_used, turn_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
    """
    result: Dict[str, Any] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                session_id, role, sender_name, document_id,
                content, ai_model_used, turn_number,
            ))
            row = cur.fetchone()
            result = dict(row)
    return result


def get_session_messages(
    session_id: str,
    after_turn: int = 0,
) -> List[Dict[str, Any]]:
    """
    Get all messages in a session after a given turn number.
    Used to load the last N raw messages for LLM context.

    Args:
        session_id: UUID of the session.
        after_turn: Only return messages with turn_number > after_turn.

    Returns:
        List of message dicts in turn order.
    """
    sql = """
        SELECT * FROM chat_messages
        WHERE session_id = %s AND turn_number > %s
        ORDER BY turn_number ASC;
    """
    rows: List[Dict[str, Any]] = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, after_turn))
            rows = [dict(r) for r in cur.fetchall()]
    return rows


def get_turn_count(session_id: str) -> int:
    """Return the current highest turn number in a session."""
    sql = "SELECT COALESCE(MAX(turn_number), 0) AS max_turn FROM chat_messages WHERE session_id = %s;"
    count: int = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id,))
            row = cur.fetchone()
            count = int(row["max_turn"]) if row else 0
    return count


# ──────────────────────────────────────────────────────────────
# Context Summaries (Compaction)
# ──────────────────────────────────────────────────────────────

def save_context_summary(
    session_id: str,
    summary: str,
    covers_up_to_turn: int,
) -> Dict[str, Any]:
    """
    Insert a new compaction summary milestone.
    Each row represents the conversation compressed up to `covers_up_to_turn`.

    Args:
        session_id: UUID of the session.
        summary: The compressed text of all messages up to covers_up_to_turn.
        covers_up_to_turn: The turn number this summary is current through.

    Returns:
        The saved summary row as a dict.
    """
    sql = """
        INSERT INTO context_summaries (session_id, summary, covers_up_to_turn)
        VALUES (%s, %s, %s)
        RETURNING *;
    """
    result: Dict[str, Any] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, summary, covers_up_to_turn))
            row = cur.fetchone()
            result = dict(row)
    return result


def get_latest_summary(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent compaction summary for a session.
    Used when building LLM context: [this summary] + [last N raw messages].

    Returns:
        The latest summary dict, or None if no compaction has happened yet.
    """
    sql = """
        SELECT * FROM context_summaries
        WHERE session_id = %s
        ORDER BY covers_up_to_turn DESC
        LIMIT 1;
    """
    result: Optional[Dict[str, Any]] = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id,))
            row = cur.fetchone()
            result = dict(row) if row else None
    return result


# ──────────────────────────────────────────────────────────────
# Web Search Logs
# ──────────────────────────────────────────────────────────────

def log_web_search(
    session_id: str,
    query: str,
    result: Optional[str] = None,
    requesting_document_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Log a silent web search performed by the Orchestrator.

    Args:
        session_id: UUID of the active session.
        query: The search query that was executed.
        result: The text result returned from the search.
        requesting_document_id: UUID of the document that triggered the search.

    Returns:
        The saved log row as a dict.
    """
    sql = """
        INSERT INTO web_search_logs (session_id, requesting_document_id, query, result)
        VALUES (%s, %s, %s, %s)
        RETURNING *;
    """
    saved: Dict[str, Any] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, requesting_document_id, query, result))
            row = cur.fetchone()
            saved = dict(row)
    logger.info(
        f"{__module_name__} - Logged web search: '{query}' "
        f"(doc={requesting_document_id}, session={session_id})"
    )
    return saved

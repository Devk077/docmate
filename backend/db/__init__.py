"""
DoqToq Groups — Database Layer
Provides PostgreSQL connection helpers and CRUD operations for rooms, documents,
sessions, chat messages, context summaries, and web search logs.
"""

from .postgres import (
    get_connection,
    create_room,
    get_all_rooms,
    get_room,
    add_document,
    get_documents_in_room,
    get_document_by_id,
    create_session,
    end_session,
    save_message,
    get_session_messages,
    get_latest_summary,
    save_context_summary,
    log_web_search,
)

__all__ = [
    "get_connection",
    "create_room",
    "get_all_rooms",
    "get_room",
    "add_document",
    "get_documents_in_room",
    "get_document_by_id",
    "create_session",
    "end_session",
    "save_message",
    "get_session_messages",
    "get_latest_summary",
    "save_context_summary",
    "log_web_search",
]

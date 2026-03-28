"""
DoqToq Groups — Chat Router

Endpoints:
  POST /api/rooms/{room_id}/sessions  → get or create a chat session
  GET  /api/rooms/{room_id}/history   → fetch chat history for current session
  POST /api/rooms/{room_id}/chat      → SSE stream: yields chunks from run_round()
"""

__module_name__ = "api.routes.chat"

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.db.postgres import (
    create_session,
    get_latest_session,
    get_room,
    get_session_messages,
    get_turn_count,
)
from api.orchestrator_store import get_or_load_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rooms", tags=["chat"])


# ── Request / Response models ──────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None  # if None, latest session is used


# ── Helpers ────────────────────────────────────────────────────

def _serialize_message(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "session_id": str(row["session_id"]),
        "role": row["role"],
        "sender_name": row.get("sender_name"),
        "document_id": str(row["document_id"]) if row.get("document_id") else None,
        "content": row["content"],
        "turn_number": row["turn_number"],
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
    }


async def _sse_generator(
    room_id: str,
    session_id: str,
    question: str,
) -> AsyncGenerator[str, None]:
    """
    Async generator that bridges the synchronous GroupOrchestrator.run_round()
    to FastAPI's async SSE response using a thread + queue pattern.

    Each chunk dict from run_round() is forwarded to the React client the moment
    the LLM yields it — true token-by-token streaming.
    """
    import queue
    import threading

    orch = get_or_load_orchestrator(room_id)
    if orch is None:
        yield f"data: {json.dumps({'error': f'Room {room_id} not found'})}\n\n"
        return

    chunk_queue: queue.Queue = queue.Queue()
    _SENTINEL = object()

    def _producer():
        """Run the synchronous generator in a dedicated thread, push to queue."""
        try:
            for chunk_dict in orch.run_round(question=question, session_id=session_id):
                chunk_queue.put(chunk_dict)
        except Exception as exc:
            chunk_queue.put({"__error__": str(exc)})
        finally:
            chunk_queue.put(_SENTINEL)

    thread = threading.Thread(target=_producer, daemon=True)
    thread.start()

    logger.info(f"{__module_name__} - SSE stream started: room={room_id}, session={session_id}")
    current_speaker: Optional[str] = None
    loop = asyncio.get_event_loop()

    while True:
        # Yield control back to the event loop while waiting for next chunk
        chunk_dict = await loop.run_in_executor(None, chunk_queue.get)

        if chunk_dict is _SENTINEL:
            break

        if isinstance(chunk_dict, dict) and "__error__" in chunk_dict:
            yield f"data: {json.dumps({'error': chunk_dict['__error__']})}\n\n"
            break

        speaker = chunk_dict.get("speaker", "")
        answer_chunk = chunk_dict.get("answer_chunk", "")
        is_complete = chunk_dict.get("is_complete", False)
        round_complete = chunk_dict.get("round_complete", False)
        web_search = chunk_dict.get("web_search_performed", False)

        # Notify frontend when a new speaker starts
        if speaker != current_speaker:
            current_speaker = speaker
            event = json.dumps({
                "event": "speaker_start",
                "speaker": speaker,
                "document_id": chunk_dict.get("document_id"),
            })
            yield f"data: {event}\n\n"

        # Yield the text chunk
        if answer_chunk:
            event = json.dumps({
                "speaker": speaker,
                "chunk": answer_chunk,
                "done": False,
                "web_search": web_search,
            })
            yield f"data: {event}\n\n"

        # Notify when this speaker is done
        if is_complete:
            event = json.dumps({
                "speaker": speaker,
                "chunk": "",
                "done": True,
                "web_search": web_search,
            })
            yield f"data: {event}\n\n"

        # Final event when all speakers are done
        if round_complete:
            yield f"data: {json.dumps({'event': 'round_complete'})}\n\n"
            logger.info(f"{__module_name__} - Round complete: room={room_id}")
            break


# ── Routes ─────────────────────────────────────────────────────

@router.post("/{room_id}/sessions", status_code=201, summary="Get or create a chat session")
async def get_or_create_session(room_id: str) -> Dict[str, Any]:
    """
    Return the latest session for a room, or create one if none exists.
    Call this when the user opens a room to get a session_id for chat.
    """
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

    session = get_latest_session(room_id)
    if session:
        logger.info(f"{__module_name__} - Resuming session {session['id']} for room {room_id}")
    else:
        session = create_session(room_id=room_id, ai_model=room.get("ai_model", "google"))
        logger.info(f"{__module_name__} - Created new session {session['id']} for room {room_id}")

    return {
        "id": str(session["id"]),
        "room_id": str(session["room_id"]),
        "ai_model": session.get("ai_model", "google"),
        "started_at": str(session["started_at"]) if session.get("started_at") else None,
    }


@router.get("/{room_id}/history", summary="Get chat history for a room")
async def get_chat_history(room_id: str, session_id: Optional[str] = None) -> list:
    """
    Return chat messages for a session.
    If session_id is omitted, uses the latest session.
    """
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

    if not session_id:
        session = get_latest_session(room_id)
        if not session:
            return []
        session_id = str(session["id"])

    messages = get_session_messages(session_id)
    return [_serialize_message(m) for m in messages]


@router.post("/{room_id}/chat", summary="Stream a chat round (SSE)")
async def chat_stream(room_id: str, body: ChatRequest) -> StreamingResponse:
    """
    Send a question to the room's GroupOrchestrator and stream the response
    as Server-Sent Events (SSE).

    The client reads the SSE stream and appends tokens to the chat UI in real-time.

    If session_id is not provided in body, the latest session is used.
    If no session exists, one is created automatically.
    """
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

    # Resolve session
    session_id = body.session_id
    if not session_id:
        session = get_latest_session(room_id)
        if not session:
            session = create_session(room_id=room_id, ai_model=room.get("ai_model", "google"))
        session_id = str(session["id"])

    logger.info(
        f"{__module_name__} - Chat request: room={room_id}, "
        f"session={session_id}, question={body.question[:60]!r}..."
    )

    return StreamingResponse(
        _sse_generator(room_id=room_id, session_id=session_id, question=body.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "Connection": "keep-alive",
        },
    )

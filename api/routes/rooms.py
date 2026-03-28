"""
DoqToq Groups — Rooms Router

Endpoints:
  GET    /api/rooms              → list all rooms
  POST   /api/rooms              → create a new room (no documents yet)
  GET    /api/rooms/{room_id}    → get single room metadata
  DELETE /api/rooms/{room_id}    → delete room + evict orchestrator
  GET    /api/rooms/{room_id}/participants → persona list for sidebar
"""

__module_name__ = "api.routes.rooms"

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.postgres import (
    create_room,
    delete_room,
    get_all_rooms,
    get_room,
)
from api.orchestrator_store import delete_orchestrator, get_or_load_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rooms", tags=["rooms"])


# ── Request / Response models ──────────────────────────────────

class CreateRoomRequest(BaseModel):
    name: str
    ai_model: str = "google"


class RoomResponse(BaseModel):
    id: str
    name: str
    ai_model: str
    document_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────

def _serialize_room(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert psycopg2 RealDict to a JSON-serializable dict."""
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "ai_model": row.get("ai_model", "google"),
        "document_count": row.get("document_count", 0),
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
    }


# ── Routes ─────────────────────────────────────────────────────

@router.get("", summary="List all rooms")
async def list_rooms() -> List[Dict[str, Any]]:
    """Return all discussion rooms ordered by most recently updated."""
    try:
        rooms = get_all_rooms()
        return [_serialize_room(r) for r in rooms]
    except Exception as e:
        logger.error(f"{__module_name__} - list_rooms error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201, summary="Create a room")
async def create_room_endpoint(body: CreateRoomRequest) -> Dict[str, Any]:
    """
    Create a new discussion room (metadata only — documents are uploaded separately).
    """
    try:
        room = create_room(name=body.name, ai_model=body.ai_model)
        logger.info(f"{__module_name__} - Created room: {room['id']} ({body.name})")
        return _serialize_room(room)
    except Exception as e:
        logger.error(f"{__module_name__} - create_room error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{room_id}", summary="Get a single room")
async def get_room_endpoint(room_id: str) -> Dict[str, Any]:
    """Return metadata for a single room."""
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    return _serialize_room(room)


@router.delete("/{room_id}", status_code=204, summary="Delete a room")
async def delete_room_endpoint(room_id: str) -> None:
    """
    Delete a room from PostgreSQL (CASCADE deletes documents/sessions).
    Also evicts the orchestrator from the in-memory cache.
    """
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

    try:
        delete_orchestrator(room_id)
        delete_room(room_id)
        logger.info(f"{__module_name__} - Deleted room {room_id}")
    except Exception as e:
        logger.error(f"{__module_name__} - delete_room error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{room_id}/participants", summary="Get room participants")
async def get_participants(room_id: str) -> List[Dict[str, Any]]:
    """
    Return the list of documents (personas) in a room.
    Loads the orchestrator if not already cached — this includes the
    embedding model warm-up on first call.
    """
    orch = get_or_load_orchestrator(room_id)
    if orch is None:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    return orch.get_participants()

"""
DoqToq Groups — Orchestrator Store

In-memory cache: room_id -> GroupOrchestrator.
Replaces st.session_state from the Streamlit era.

Orchestrators are loaded from PostgreSQL on first access
and kept alive for the lifetime of the API process.
"""

__module_name__ = "api.orchestrator_store"

import logging
from typing import Dict, Optional

from backend.group_rag_engine import GroupOrchestrator
from backend.db.postgres import get_room

logger = logging.getLogger(__name__)

# room_id (str UUID) -> live GroupOrchestrator
_store: Dict[str, GroupOrchestrator] = {}


def get_orchestrator(room_id: str) -> Optional[GroupOrchestrator]:
    """Return cached orchestrator, or None if not loaded yet."""
    return _store.get(room_id)


def set_orchestrator(room_id: str, orch: GroupOrchestrator) -> None:
    """Store an orchestrator in cache."""
    _store[room_id] = orch
    logger.info(f"{__module_name__} - Cached orchestrator for room {room_id}")


def delete_orchestrator(room_id: str) -> None:
    """Remove an orchestrator from cache (e.g. after room deletion)."""
    if room_id in _store:
        del _store[room_id]
        logger.info(f"{__module_name__} - Evicted orchestrator for room {room_id}")


def get_or_load_orchestrator(room_id: str) -> Optional[GroupOrchestrator]:
    """
    Return cached orchestrator, loading from DB if necessary.

    On first call for a room:
      1. Fetches room metadata from PostgreSQL
      2. Creates a GroupOrchestrator
      3. Calls load_room_documents() to restore all RAG instances
      4. Caches for the process lifetime

    Returns None if the room does not exist in DB.
    """
    if room_id in _store:
        logger.debug(f"{__module_name__} - Cache hit for room {room_id}")
        return _store[room_id]

    logger.info(f"{__module_name__} - Cache miss — loading room {room_id} from DB")
    room = get_room(room_id)
    if not room:
        logger.warning(f"{__module_name__} - Room {room_id} not found in DB")
        return None

    model_provider = room.get("ai_model", "google")
    orch = GroupOrchestrator(
        room_id=room_id,
        model_provider=model_provider,
        streaming=True,
    )
    orch.load_room_documents()
    _store[room_id] = orch
    logger.info(
        f"{__module_name__} - Loaded room '{room['name']}' "
        f"({len(orch)} docs) into cache"
    )
    return orch

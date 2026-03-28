"""
DoqToq Groups — Documents Router

Endpoints:
  GET    /api/rooms/{room_id}/documents               → list documents in room
  POST   /api/rooms/{room_id}/documents               → upload + index + persona name
  DELETE /api/rooms/{room_id}/documents/{document_id} → remove doc + delete collection
"""

__module_name__ = "api.routes.documents"

import logging
import os
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.db.postgres import (
    add_document,
    get_documents_in_room,
    get_room,
    remove_document,
)
from backend.prompts.group_prompts import generate_persona_name
from backend.vectorstore.naming import make_collection_name
from api.orchestrator_store import get_or_load_orchestrator, get_orchestrator, delete_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rooms", tags=["documents"])

# Upload base directory (matches what Streamlit used)
UPLOAD_BASE = os.path.join("data", "uploads")


# ── Helpers ────────────────────────────────────────────────────

def _serialize_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "room_id": str(row["room_id"]),
        "filename": row["filename"],
        "persona_name": row["persona_name"],
        "qdrant_collection": row["qdrant_collection"],
        "file_path": row.get("file_path"),
        "added_at": str(row["added_at"]) if row.get("added_at") else None,
    }


def _save_file(file_bytes: bytes, filename: str, room_id: str) -> str:
    """Save uploaded bytes to data/uploads/{room_id}/{filename}."""
    room_upload_dir = os.path.join(UPLOAD_BASE, room_id)
    os.makedirs(room_upload_dir, exist_ok=True)
    file_path = os.path.join(room_upload_dir, filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return file_path


# ── Routes ─────────────────────────────────────────────────────

@router.get("/{room_id}/documents", summary="List documents in a room")
async def list_documents(room_id: str) -> List[Dict[str, Any]]:
    """Return all documents registered to a room."""
    if not get_room(room_id):
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    docs = get_documents_in_room(room_id)
    return [_serialize_doc(d) for d in docs]


@router.post("/{room_id}/documents", status_code=201, summary="Upload and index a document")
async def upload_document(
    room_id: str,
    file: UploadFile = File(...),
    ai_model: str = Form("google"),
) -> Dict[str, Any]:
    """
    Upload a document to a room:
      1. Save file to disk
      2. Generate persona name via LLM
      3. Index into Qdrant (create new collection)
      4. Register in PostgreSQL
      5. Register in the live orchestrator (if already loaded)

    Returns the created document row.
    """
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

    # 1. Save file
    file_bytes = await file.read()
    filename = file.filename or f"document_{uuid.uuid4().hex[:8]}"
    logger.info(f"{__module_name__} - Saving '{filename}' for room {room_id}")
    try:
        file_path = _save_file(file_bytes, filename, room_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # 2. Generate persona name (runs synchronous LLM call — offload to thread)
    logger.info(f"{__module_name__} - Generating persona name for '{filename}' using model '{ai_model}'")
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        persona_name = await loop.run_in_executor(
            None,
            lambda: generate_persona_name(file_path=file_path, model_provider=ai_model),
        )
        logger.info(f"{__module_name__} - Generated persona name: '{persona_name}'")
    except Exception as e:
        logger.warning(f"{__module_name__} - Persona generation failed ({e}), using filename fallback")
        persona_name = os.path.splitext(filename)[0].replace("_", " ").title()

    # 3. Compute collection name
    collection_name = make_collection_name(room_id, filename)
    logger.info(f"{__module_name__} - Collection: {collection_name}")

    # 4. Index into Qdrant via orchestrator
    orch = get_or_load_orchestrator(room_id)
    if orch is None:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")

    placeholder_id = f"tmp_{uuid.uuid4().hex[:8]}"
    try:
        orch.add_document(
            document_id=placeholder_id,
            persona_name=persona_name,
            collection_name=collection_name,
            file_path=file_path,
        )
    except Exception as e:
        logger.error(f"{__module_name__} - Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

    # 5. Register in PostgreSQL (get real UUID)
    try:
        doc_row = add_document(
            room_id=room_id,
            filename=filename,
            persona_name=persona_name,
            qdrant_collection=collection_name,
            file_path=file_path,
        )
    except Exception as e:
        logger.error(f"{__module_name__} - DB registration failed: {e}")
        raise HTTPException(status_code=500, detail=f"DB registration failed: {e}")

    # Swap placeholder id with real DB id in orchestrator
    real_id = str(doc_row["id"])
    if placeholder_id in orch._docs:
        doc_obj = orch._docs.pop(placeholder_id)
        doc_obj.document_id = real_id
        orch._docs[real_id] = doc_obj
        logger.info(f"{__module_name__} - Swapped placeholder -> real_id={real_id}")

    logger.info(f"{__module_name__} - '{persona_name}' added to room {room_id}")
    return _serialize_doc(doc_row)


@router.delete(
    "/{room_id}/documents/{document_id}",
    status_code=204,
    summary="Remove a document from a room",
)
async def delete_document(room_id: str, document_id: str) -> None:
    """
    Remove a document:
      1. Remove from live orchestrator (if loaded)
      2. Delete from PostgreSQL
      3. Evict the orchestrator cache so next room open reloads from DB cleanly
    The vector collection is left in place (can be GC'd later).
    """
    orch = get_orchestrator(room_id)  # don't trigger a load just for deletion
    if orch:
        orch.remove_document(document_id)

    try:
        remove_document(document_id)
        logger.info(f"{__module_name__} - Removed document {document_id} from room {room_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Evict cache so next GET /participants reloads fresh from DB
    delete_orchestrator(room_id)
    logger.info(f"{__module_name__} - Evicted orchestrator cache for room {room_id} after doc removal")


@router.get(
    "/{room_id}/documents/{document_id}/preview",
    summary="Serve a document file for in-browser preview",
)
async def preview_document(room_id: str, document_id: str):
    """
    Return the raw file bytes so the browser can render it.
    PDFs open inline; text files as plain text.
    """
    from fastapi.responses import FileResponse
    from backend.db.postgres import get_documents_in_room

    docs = get_documents_in_room(room_id)
    doc = next((d for d in docs if str(d["id"]) == document_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("file_path") or ""
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    media_type_map = {
        ".pdf":  "application/pdf",
        ".txt":  "text/plain",
        ".md":   "text/plain",
        ".csv":  "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    media_type = media_type_map.get(ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

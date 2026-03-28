"""
DoqToq Groups — Room Manager

Handles creating rooms, uploading/indexing documents into rooms,
and restoring an existing room's GroupOrchestrator from the database.

This module is the bridge between the UI (Phase 5) and the backend (Phases 1-4).
"""

__module_name__ = "app.room_manager"

import os
import tempfile
import logging
from pathlib import Path
from typing import List, Optional

import streamlit as st

from backend.db.postgres import (
    add_document,
    create_room,
    create_session,
    delete_room,
    get_all_rooms,
    get_latest_session,
    get_room,
    remove_document,
    update_room_model,
)
from backend.group_rag_engine import GroupOrchestrator
from backend.prompts.group_prompts import generate_persona_name
from backend.vectorstore.naming import delete_collection, make_collection_name

logger = logging.getLogger(__name__)

# Directory where uploaded files are stored for the room
_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "uploads"
)
os.makedirs(_UPLOAD_DIR, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# Room Creation
# ──────────────────────────────────────────────────────────────

def render_new_room_form() -> None:
    """
    Render the New Discussion Room creation form.
    Handles the full flow: name input → file upload → indexing → room ready.
    """
    st.markdown("## 🚀 Start a New Discussion Room")
    st.markdown(
        "Upload **2 or more documents** and give your room a name. "
        "Each document will be assigned a unique AI persona and can be questioned simultaneously."
    )

    with st.form("new_room_form", clear_on_submit=False):
        room_name = st.text_input(
            "Room Name",
            placeholder="e.g. Climate Policy Review, Q3 Strategy Session",
            max_chars=80,
        )

        uploaded_files = st.file_uploader(
            "Upload Documents (PDF, TXT, MD, DOCX — up to 10 files)",
            type=["pdf", "txt", "md", "docx", "csv"],
            accept_multiple_files=True,
            help="Each document becomes a participant in the discussion. Upload at least 1."
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            model_choice = st.selectbox(
                "AI Model",
                options=["Gemini (Google)", "Mistral AI", "Ollama"],
                index=0,
            )
        with col2:
            temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)

        submitted = st.form_submit_button("🎯 Start Discussion", use_container_width=True)

        if submitted:
            if not room_name.strip():
                st.error("Please enter a room name.")
                return
            if not uploaded_files:
                st.error("Please upload at least one document.")
                return

            model_provider = _model_choice_to_provider(model_choice)
            room_id = create_room_from_files(
                name=room_name.strip(),
                uploaded_files=uploaded_files,
                model_provider=model_provider,
                temperature=temperature,
            )
            if room_id:
                st.session_state.active_room_id = room_id
                st.session_state.app_view = "room"
                # Do NOT null the orchestrator — keep the freshly-built one alive
                # so load_room() is not called again on the immediate rerun
                st.rerun()


def create_room_from_files(
    name: str,
    uploaded_files: list,
    model_provider: str = "google",
    temperature: float = 0.7,
) -> Optional[str]:
    """
    Full room creation pipeline:
    1. Save room to PostgreSQL
    2. Save each uploaded file to disk
    3. Generate persona name via LLM
    4. Create vector collection and index document
    5. Save document registration to PostgreSQL
    6. Create initial session
    7. Return room_id

    Args:
        name: User-provided room name.
        uploaded_files: List of Streamlit UploadedFile objects.
        model_provider: 'google', 'mistral', or 'ollama'
        temperature: LLM temperature for this room.

    Returns:
        room_id string if successful, None on failure.
    """
    try:
        # Step 1: Create room in DB
        logger.info(f"{__module_name__} - [1/6] Creating room in DB: name='{name}', model={model_provider}")
        room = create_room(name=name, ai_model=model_provider)
        room_id = str(room["id"])
        logger.info(f"{__module_name__} - [1/6] OK Room created: {room_id}")

        # Step 2-5: Process each file
        progress = st.progress(0, text="Setting up your Discussion Room...")
        total = len(uploaded_files)

        # Build orchestrator for indexing
        logger.info(f"{__module_name__} - [2/6] Initialising GroupOrchestrator for room {room_id}")
        orchestrator = GroupOrchestrator(
            room_id=room_id,
            model_provider=model_provider,
            temperature=temperature,
            streaming=True,
        )
        logger.info(f"{__module_name__} - [2/6] OK Orchestrator ready")

        for i, uploaded_file in enumerate(uploaded_files):
            progress_pct = int((i / total) * 100)
            progress.progress(
                progress_pct,
                text=f"Indexing '{uploaded_file.name}' ({i+1}/{total})..."
            )
            logger.info(f"{__module_name__} - [3/6] Processing file {i+1}/{total}: {uploaded_file.name}")

            # Save file to disk
            file_path = _save_uploaded_file(uploaded_file, room_id)
            if not file_path:
                st.warning(f"⚠️ Could not save '{uploaded_file.name}', skipping.")
                logger.warning(f"{__module_name__} - Skipping '{uploaded_file.name}' — save failed")
                continue
            logger.info(f"{__module_name__} - File saved to: {file_path}")

            # Generate collection name
            collection_name = make_collection_name(room_id, uploaded_file.name)
            logger.info(f"{__module_name__} - Collection name: {collection_name}")

            # Generate persona name via LLM
            logger.info(f"{__module_name__} - [4/6] Generating persona name for: {uploaded_file.name}")
            with st.spinner(f"🤖 Naming document: {uploaded_file.name}..."):
                persona_name = generate_persona_name(
                    file_path=file_path,
                    model_provider=model_provider,
                )
            logger.info(f"{__module_name__} - [4/6] OK Persona name: '{persona_name}'")

            # Add to orchestrator (indexes into vector DB)
            logger.info(f"{__module_name__} - [5/6] Indexing '{persona_name}' into vector DB...")
            with st.spinner(f"🔍 Indexing: {persona_name}..."):
                room_doc = orchestrator.add_document(
                    document_id="placeholder",
                    persona_name=persona_name,
                    collection_name=collection_name,
                    file_path=file_path,
                )
            logger.info(f"{__module_name__} - [5/6] OK Indexed into Qdrant collection: {collection_name}")

            # Save document to PostgreSQL (get real UUID)
            logger.info(f"{__module_name__} - Saving document to PostgreSQL...")
            doc_row = add_document(
                room_id=room_id,
                filename=uploaded_file.name,
                persona_name=persona_name,
                qdrant_collection=collection_name,
                file_path=file_path,
            )
            # Update the orchestrator's reference with real document_id
            real_doc_id = str(doc_row["id"])
            if "placeholder" in orchestrator._docs:
                room_doc_obj = orchestrator._docs.pop("placeholder")
                room_doc_obj.document_id = real_doc_id
                orchestrator._docs[real_doc_id] = room_doc_obj
            logger.info(f"{__module_name__} - OK Document saved: doc_id={real_doc_id}")

        progress.progress(95, text="Creating chat session...")
        logger.info(f"{__module_name__} - [6/6] Creating initial chat session...")
        create_session(room_id=room_id, ai_model=model_provider)
        logger.info(f"{__module_name__} - [6/6] OK Session created")

        progress.progress(100, text="Ready!")
        st.success(f"🎉 **{name}** is ready! {total} document(s) indexed.")
        logger.info(f"{__module_name__} - OK Room '{name}' fully ready ({total} docs)")

        # Store orchestrator in session state
        st.session_state.room_orchestrator = orchestrator
        return room_id

    except Exception as e:
        logger.error(f"{__module_name__} - Room creation failed: {e}")
        st.error(f"Failed to create room: {str(e)}")
        return None


# ──────────────────────────────────────────────────────────────
# Room Restoration
# ──────────────────────────────────────────────────────────────

def load_room(room_id: str) -> Optional[GroupOrchestrator]:
    """
    Restore a GroupOrchestrator from the database for an existing room.
    Called when user navigates back to a room they previously created.
    """
    logger.info(f"{__module_name__} - load_room() START: room_id={room_id}")
    room = get_room(room_id)
    if not room:
        st.error(f"Room not found: {room_id}")
        logger.error(f"{__module_name__} - load_room() FAILED: room {room_id} not in DB")
        return None

    model_provider = room.get("ai_model", "google")
    logger.info(f"{__module_name__} - load_room() room='{room['name']}', model={model_provider}")

    orchestrator = GroupOrchestrator(
        room_id=room_id,
        model_provider=model_provider,
        streaming=True,
    )
    logger.info(f"{__module_name__} - load_room() orchestrator created, loading documents...")

    with st.spinner("Restoring documents from your last session..."):
        orchestrator.load_room_documents()

    logger.info(
        f"{__module_name__} - load_room() DONE: loaded {len(orchestrator)} doc(s) "
        f"for room '{room['name']}'"
    )
    return orchestrator


def get_or_create_session(room_id: str, model_provider: str) -> str:
    """
    Get the latest open session for a room, or create a new one.

    Returns:
        session_id string
    """
    latest = get_latest_session(room_id)
    if latest and not latest.get("ended_at"):
        return str(latest["id"])
    session = create_session(room_id=room_id, ai_model=model_provider)
    return str(session["id"])


# ──────────────────────────────────────────────────────────────
# Room Deletion
# ──────────────────────────────────────────────────────────────

def remove_room(room_id: str) -> None:
    """
    Delete a room and clean up all vector collections.
    Called from the room list when user clicks "Delete Room".
    """
    from backend.db.postgres import get_documents_in_room
    docs = get_documents_in_room(room_id)
    for doc in docs:
        collection = doc.get("qdrant_collection")
        if collection:
            delete_collection(collection)

    delete_room(room_id)
    logger.info(f"{__module_name__} - Deleted room: {room_id}")


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _save_uploaded_file(uploaded_file, room_id: str) -> Optional[str]:
    """Save a Streamlit UploadedFile to disk under data/uploads/{room_id}/."""
    room_dir = os.path.join(_UPLOAD_DIR, room_id)
    os.makedirs(room_dir, exist_ok=True)

    file_path = os.path.join(room_dir, uploaded_file.name)
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        logger.error(f"{__module_name__} - Failed to save '{uploaded_file.name}': {e}")
        return None


def _model_choice_to_provider(model_choice: str) -> str:
    mapping = {
        "Gemini (Google)": "google",
        "Mistral AI": "mistral",
        "Ollama": "ollama",
    }
    return mapping.get(model_choice, "google")

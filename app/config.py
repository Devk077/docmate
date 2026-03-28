__module_name__ = "config"

import streamlit as st


def init_session_state() -> None:
    # ── Single-doc mode (legacy) ──────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "qa_chain" not in st.session_state:
        st.session_state.qa_chain = None

    # ── Groups mode ───────────────────────────────────────────

    # Which view is active: "home" | "room" | "new_room"
    if "app_view" not in st.session_state:
        st.session_state.app_view = "home"

    # UUID string of the currently open room (None = no room open)
    if "active_room_id" not in st.session_state:
        st.session_state.active_room_id = None

    # Live GroupOrchestrator instance for the active room
    if "room_orchestrator" not in st.session_state:
        st.session_state.room_orchestrator = None

    # Active PostgreSQL session UUID for the open room
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None

    # Group chat history: list of dicts
    # {role, speaker, document_id, content, web_search_performed}
    if "group_chat_history" not in st.session_state:
        st.session_state.group_chat_history = []

    # Persona name → colour palette index (for bubble colouring)
    if "persona_color_map" not in st.session_state:
        st.session_state.persona_color_map = {}

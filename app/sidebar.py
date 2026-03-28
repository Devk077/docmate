__module_name__ = "sidebar"

import os

import streamlit as st

from app.utils import load_svg_icon
from backend.db.postgres import get_all_rooms
from backend.embedder import get_model_info, list_available_models


def render_sidebar() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    fader_icon_path = os.path.join(project_root, "assets", "faders-horizontal-fill.svg")
    sparkle_icon_path = os.path.join(project_root, "assets", "sparkle-light.svg")
    fader_icon_b64 = load_svg_icon(fader_icon_path)
    sparkle_icon_b64 = load_svg_icon(sparkle_icon_path)

    # ── DoqToq logo at the top of sidebar ────────────────────
    st.sidebar.markdown(
        "<p style='font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,#5B8AF5,#C65BF5);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:4px;'>📄 DoqToq</p>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    # ── Discussion Rooms List ─────────────────────────────────
    st.sidebar.markdown(
        "<p class='room-list-header'>💬 Discussion Rooms</p>",
        unsafe_allow_html=True,
    )

    # New Room button
    if st.sidebar.button("＋ New Room", use_container_width=True, key="sidebar_new_room_btn"):
        st.session_state.app_view = "new_room"
        st.session_state.active_room_id = None
        st.session_state.room_orchestrator = None
        st.rerun()

    # List all existing rooms
    try:
        rooms = get_all_rooms()
    except Exception:
        rooms = []

    if rooms:
        for room in rooms:
            room_id = str(room["id"])
            room_name = room.get("name", "Unnamed Room")
            is_active = st.session_state.get("active_room_id") == room_id

            # Room button (no custom HTML — use native Streamlit for reliability)
            btn_label = f"{'▶ ' if is_active else ''}{room_name}"
            col1, col2 = st.sidebar.columns([4, 1])
            with col1:
                if st.button(
                    btn_label,
                    key=f"room_btn_{room_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.active_room_id = room_id
                    st.session_state.app_view = "room"
                    st.session_state.room_orchestrator = None
                    st.session_state.group_chat_history = []
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"del_room_{room_id}", help="Delete this room"):
                    from app.room_manager import remove_room
                    remove_room(room_id)
                    if st.session_state.get("active_room_id") == room_id:
                        st.session_state.active_room_id = None
                        st.session_state.app_view = "home"
                        st.session_state.room_orchestrator = None
                    st.rerun()
    else:
        st.sidebar.markdown(
            "<p style='color:#718096;font-size:0.85rem;padding:8px 0;'>No rooms yet — create one!</p>",
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")

    # ── Settings Header ───────────────────────────────────────
    if fader_icon_b64:
        st.sidebar.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
            <img src="data:image/svg+xml;base64,{fader_icon_b64}"
                 style="width: 24px; height: 24px; opacity: 0.8;"
                 alt="Settings">
            <h3 style="margin: 0; font-size: 1rem; font-weight: 600; color:#e2e8f0;">Settings</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown("### ⚙️ Settings")

    # Model selection
    model_choice = st.sidebar.selectbox(
        "Language Model",
        options=["Gemini (Google)", "Mistral AI", "Ollama"],
        index=0,
        key="sidebar_llm_choice",
    )
    st.session_state.llm_choice = model_choice

    # Temperature
    temperature = st.sidebar.slider(
        "Temperature",
        min_value=0.0, max_value=1.0, value=0.7, step=0.1,
        key="sidebar_temperature",
    )
    st.session_state.temperature = temperature

    # Streaming
    streaming_enabled = st.sidebar.toggle(
        "Enable Streaming",
        value=True,
        key="sidebar_streaming",
    )
    st.session_state.streaming_enabled = streaming_enabled

    if streaming_enabled:
        streaming_mode = st.sidebar.selectbox(
            "Streaming Style",
            options=["Character by Character", "Word by Word", "Instant"],
            index=0,
            key="sidebar_streaming_mode_select",
        )
        if streaming_mode == "Character by Character":
            streaming_delay = st.sidebar.slider(
                "Character Speed", 0.005, 0.1, 0.02, 0.005,
                format="%.3f", key="sidebar_char_speed",
            )
            st.session_state.streaming_delay = streaming_delay
            st.session_state.streaming_mode = "character"
        elif streaming_mode == "Word by Word":
            streaming_delay = st.sidebar.slider(
                "Word Speed", 0.05, 0.5, 0.15, 0.05,
                format="%.2f", key="sidebar_word_speed",
            )
            st.session_state.streaming_delay = streaming_delay
            st.session_state.streaming_mode = "word"
        else:
            st.session_state.streaming_delay = 0.0
            st.session_state.streaming_mode = "instant"
    else:
        st.session_state.streaming_delay = 0.0
        st.session_state.streaming_mode = "instant"

    # Top-K
    top_k = st.sidebar.slider(
        "Chunks to Retrieve (k)", 1, 10, 4,
        key="sidebar_top_k",
    )
    st.session_state.top_k = top_k

    st.sidebar.markdown("---")

    # Embedding Models
    if sparkle_icon_b64:
        st.sidebar.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 12px; margin: 12px 0;">
            <img src="data:image/svg+xml;base64,{sparkle_icon_b64}"
                 style="width: 24px; height: 24px; opacity: 0.8;"
                 alt="Embeddings">
            <h3 style="margin: 0; font-size: 1rem; font-weight: 600; color:#e2e8f0;">Embeddings</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown("### ✨ Embeddings")

    embedding_provider = st.sidebar.selectbox(
        "Embedding Provider",
        options=["huggingface", "mistral"],
        index=0,
        key="sidebar_emb_provider",
    )
    st.session_state.embedding_provider = embedding_provider

    available_models = list_available_models(embedding_provider)[embedding_provider]
    embedding_model = st.sidebar.selectbox(
        "Embedding Model",
        options=list(available_models.keys()),
        index=0,
        key="sidebar_emb_model",
    )
    st.session_state.embedding_model = embedding_model

    if st.sidebar.button("Model Info", icon=":material/info:", key="sidebar_model_info_btn"):
        model_info = get_model_info(embedding_provider, embedding_model)
        if "error" not in model_info:
            st.sidebar.success(f"**{model_info['type']}**")
            local_status = ":material/check_circle:" if model_info["local"] else ":material/cancel:"
            st.sidebar.info("Local", icon=local_status)
        else:
            st.sidebar.error(model_info["error"])

    st.sidebar.markdown("---")

    # Clear cache
    if st.sidebar.button("Clear Document Cache", icon=":material/delete:", key="sidebar_clear_cache"):
        try:
            from backend.vectorstore.vector_db import clear_vectorstore
            clear_vectorstore()
        except Exception:
            pass
        st.session_state.qa_chain = None
        st.session_state.chat_history = []
        if hasattr(st.session_state, "current_file_path"):
            delattr(st.session_state, "current_file_path")
        st.sidebar.success("✅ Cache cleared!")
        st.rerun()

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown(
        "<p style='color:#4a5568;font-size:0.78rem;text-align:center;'>Built with ❤️ by DoqToq</p>",
        unsafe_allow_html=True,
    )

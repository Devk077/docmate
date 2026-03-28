__module_name__ = "main"

import os
import sys
import warnings

# ── Environment setup (must be first) ──────────────────────────
os.environ["TORCH_WARN"] = "0"
os.environ["PYTORCH_DISABLE_TORCH_FUNCTION_WARN"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["STREAMLIT_DISABLE_WATCHDOG_WARNING"] = "1"
os.environ["STREAMLIT_FILE_WATCHER_TYPE"] = "none"

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=UserWarning, message=".*torch.*")

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from utils.torch_compatibility import apply_streamlit_fixes
    apply_streamlit_fixes()
    from utils.logging_method import setup_logger
    logger = setup_logger(
        log_file=os.path.join(project_root, "logs", "app.log"),
        level="INFO",
        timezone_str="Asia/Kolkata",
    )
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    print("Warning: Could not import torch compatibility fixes")

import streamlit as st

st.set_page_config(
    page_title="DoqToq",
    page_icon=":material/folder_open:",
    layout="wide",                     # ← Groups need wide layout
    initial_sidebar_state="expanded",  # ← Sidebar always shown for room nav
)

from app.chat import render_chat_interface
from app.config import init_session_state
from app.sidebar import render_sidebar
from app.styles import inject_custom_css
from app.uploader import handle_upload
from app.utils import load_svg_icon
from backend.rag_engine import DocumentRAG

inject_custom_css()
init_session_state()
render_sidebar()

# ── Log app start once ────────────────────────────────────────
if "app_started_logged" not in st.session_state:
    logger.info(f"{__module_name__} - Application started")
    st.session_state.app_started_logged = True

# ══════════════════════════════════════════════════════════════
# VIEW ROUTER  (runs after all functions below are defined)
# ══════════════════════════════════════════════════════════════

def _run_router():
    app_view = st.session_state.get("app_view", "home")
    if app_view == "new_room":
        _render_header()
        from app.room_manager import render_new_room_form
        render_new_room_form()
    elif app_view == "room" and st.session_state.get("active_room_id"):
        _render_room_view()
    else:
        _render_home_view()


# ══════════════════════════════════════════════════════════════
# View Renderers
# ══════════════════════════════════════════════════════════════

def _render_header():
    """Render the DoqToq logo/title bar."""
    document_icon_path = os.path.join(project_root, "assets", "scroll-light.svg")
    document_icon_b64 = load_svg_icon(document_icon_path)

    if document_icon_b64:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;margin-bottom:0.2rem;">
                <img src="data:image/svg+xml;base64,{document_icon_b64}"
                     style="width:36px;height:36px;margin-right:10px;" alt="DoqToq logo">
                <h1 class="doqtoq-title" style="margin:0;">DoqToq</h1>
            </div>
            <div class="doqtoq-subtitle">Documents that talk — DoqToq Groups</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<h1 class="doqtoq-title">📄 DoqToq</h1>', unsafe_allow_html=True)


def _render_home_view():
    """
    Home screen: shows the DoqToq hero + existing rooms grid
    + the original single-doc upload flow.
    """
    from app.room_manager import load_room, get_or_create_session
    from backend.db.postgres import get_all_rooms

    _render_header()

    # ── Groups section ─────────────────────────────────────────
    st.markdown("## 💬 Discussion Rooms")

    col_new, _ = st.columns([2, 5])
    with col_new:
        if st.button("＋ New Discussion Room", use_container_width=True, type="primary"):
            st.session_state.app_view = "new_room"
            st.rerun()

    # Render existing rooms as a simple grid
    try:
        rooms = get_all_rooms()
    except Exception:
        rooms = []

    if rooms:
        cols = st.columns(min(len(rooms), 3))
        for i, room in enumerate(rooms):
            room_id = str(room["id"])
            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div class="home-room-card" style="pointer-events:none;">
                        <div class="home-room-card-title">💬 {room['name']}</div>
                        <div class="home-room-card-meta">Model: {room.get('ai_model','google')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("Open →", key=f"open_room_{room_id}", use_container_width=True):
                    st.session_state.active_room_id = room_id
                    st.session_state.app_view = "room"
                    st.session_state.room_orchestrator = None
                    st.session_state.group_chat_history = []
                    st.rerun()
    else:
        st.info("No Discussion Rooms yet. Create one with the button above!", icon="💡")

    st.markdown("---")

    # ── Legacy single-doc mode ─────────────────────────────────
    st.markdown("## 📄 Single Document Mode")
    st.markdown("Upload a single document to chat with it directly (original DoqToq experience).")

    uploaded_file = st.file_uploader(
        "Upload a PDF, TXT, JSON or Markdown document",
        type=["pdf", "txt", "json", "md"],
    )

    current_file_name = uploaded_file.name if uploaded_file else "No file uploaded"
    last_logged_file = st.session_state.get("last_logged_file", None)
    if last_logged_file != current_file_name:
        logger.info(f"{__module_name__} - File uploaded: {current_file_name}")
        st.session_state.last_logged_file = current_file_name

    if uploaded_file:
        from app.uploader import handle_upload
        file_path = handle_upload(uploaded_file)

        current_file = getattr(st.session_state, "current_file_path", None)
        is_new_document = current_file != file_path

        if is_new_document:
            st.session_state.qa_chain = None
            st.session_state.chat_history = []
            st.session_state.current_file_path = file_path
            st.info(f"New document detected: {uploaded_file.name}", icon=":material/docs:")

        if not st.session_state.qa_chain:
            with st.spinner("Reading and indexing your document..."):
                llm_choice = st.session_state.get("llm_choice", "Gemini (Google)")
                model_provider = (
                    "google" if llm_choice == "Gemini (Google)"
                    else "mistral" if llm_choice == "Mistral AI" else "ollama"
                )
                embedding_provider = st.session_state.get("embedding_provider", "huggingface")
                embedding_model = st.session_state.get("embedding_model", "all-MiniLM-L6-v2")
                temperature = st.session_state.get("temperature", 0.7)
                top_k = st.session_state.get("top_k", 4)
                streaming_enabled = st.session_state.get("streaming_enabled", True)

                st.session_state.qa_chain = DocumentRAG(
                    file_path=file_path,
                    model_provider=model_provider,
                    temperature=temperature,
                    top_k=top_k,
                    embedding_provider=embedding_provider,
                    embedding_model=embedding_model,
                    streaming=streaming_enabled,
                )

        if st.session_state.qa_chain:
            llm_choice = st.session_state.get("llm_choice", "Gemini (Google)")
            model_provider = (
                "google" if llm_choice == "Gemini (Google)"
                else "mistral" if llm_choice == "Mistral AI" else "ollama"
            )
            temperature = st.session_state.get("temperature", 0.7)
            top_k = st.session_state.get("top_k", 4)
            streaming_enabled = st.session_state.get("streaming_enabled", True)
            embedding_provider = st.session_state.get("embedding_provider", "huggingface")
            embedding_model = st.session_state.get("embedding_model", "all-MiniLM-L6-v2")

            st.session_state.qa_chain.update_settings(
                temperature=temperature, top_k=top_k,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                model_provider=model_provider,
                streaming=streaming_enabled,
            )

        st.success(
            "Your document has awakened! Ready for questions.",
            icon=":material/check_circle:",
        )
        render_chat_interface()
    else:
        st.info("Please upload a document to begin.", icon="📎")


def _render_room_view():
    """
    Discord-style two-column Discussion Room view.
    Left 75% = chat panel. Right 25% = participants panel.
    """
    from app.room_manager import load_room, get_or_create_session
    from app.styles import get_persona_color
    from backend.db.postgres import get_room, get_documents_in_room

    room_id = st.session_state.active_room_id
    room = get_room(room_id)
    if not room:
        st.error("Room not found.")
        st.session_state.app_view = "home"
        st.rerun()
        return

    # Room header
    st.markdown(
        f"<h2 style='margin-bottom:4px;'>💬 {room['name']}</h2>"
        f"<p style='color:#718096;margin-top:0;font-size:0.85rem;'>Discussion Room · {room.get('ai_model','google').title()} model</p>",
        unsafe_allow_html=True,
    )

    # Back to home
    if st.button("← Back to Home", key="room_back_btn"):
        st.session_state.app_view = "home"
        st.session_state.active_room_id = None
        st.session_state.room_orchestrator = None
        st.rerun()

    # Load/restore orchestrator
    orchestrator = st.session_state.get("room_orchestrator")
    if orchestrator is None:
        with st.spinner("Loading room — this may take ~10s on first open (loading AI models)..."):
            try:
                orchestrator = load_room(room_id)
                st.session_state.room_orchestrator = orchestrator
            except Exception as e:
                st.error(f"**Failed to load room:** {str(e)}")
                st.info("💡 If the vector store is missing, delete this room and re-create it.")
                return

    if orchestrator is None:
        st.error("Could not load room. Please try again.")
        return

    # Get or create active session
    session_id = st.session_state.get("active_session_id")
    if not session_id:
        session_id = get_or_create_session(room_id, room.get("ai_model", "google"))
        st.session_state.active_session_id = session_id

    # Two-column layout
    chat_col, panel_col = st.columns([3, 1], gap="medium")

    # ── Participants Panel (right column) ─────────────────────
    with panel_col:
        st.markdown(
            "<div class='participant-panel-header'>👥 PARTICIPANTS</div>",
            unsafe_allow_html=True,
        )
        participants = orchestrator.get_participants()
        if participants:
            for p in participants:
                color = get_persona_color(p["persona_name"])
                status = "spent" if p.get("spent") else "active"
                status_label = "Idle this turn" if p.get("spent") else "Ready"
                st.markdown(
                    f"""
                    <div class="participant-card">
                        <div class="participant-dot {status}" style="background:{color};color:{color};"></div>
                        <div class="participant-name">{p['persona_name']}</div>
                        <div class="participant-status">{status_label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='color:#718096;font-size:0.85rem;'>No documents loaded.</p>",
                unsafe_allow_html=True,
            )

        # Autocomplete hint
        if participants:
            names = [p["persona_name"] for p in participants]
            st.markdown(
                "<p style='color:#4a5568;font-size:0.75rem;margin-top:12px;'>"
                "💡 Use @name to address a specific document</p>",
                unsafe_allow_html=True,
            )
            # Show available names as chips
            chips = " ".join(
                f"<code style='font-size:0.72rem;background:#1a202c;color:#5B8AF5;padding:2px 6px;border-radius:4px;margin:2px;'>@{n}</code>"
                for n in names
            )
            st.markdown(chips, unsafe_allow_html=True)

    # ── Chat Panel (left column) ──────────────────────────────
    with chat_col:
        group_history = st.session_state.get("group_chat_history", [])

        # Render history
        for msg in group_history:
            role = msg.get("role")
            speaker = msg.get("speaker", "")
            content = msg.get("content", "")

            if role == "user":
                with st.chat_message("user"):
                    st.markdown(content)
            elif role in ("document", "orchestrator"):
                color = get_persona_color(speaker)
                with st.chat_message("assistant"):
                    st.markdown(
                        f"<span class='chat-bubble-speaker-label' style='color:{color};'>● {speaker}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(content)

        # Chat input
        user_input = st.chat_input(
            "Ask the room a question, or @mention a document...",
            key="group_chat_input",
        )

        if user_input:
            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(user_input)

            # Add to history
            group_history.append({
                "role": "user",
                "speaker": "You",
                "content": user_input,
            })

            # Orchestrator status
            status_placeholder = st.empty()
            status_placeholder.markdown(
                "<div class='orchestrator-status'>"
                "<div class='status-dot'></div>Routing to documents...</div>",
                unsafe_allow_html=True,
            )

            # Run the round
            for chunk in orchestrator.run_round(
                question=user_input,
                session_id=session_id,
            ):
                speaker = chunk.get("speaker", "")
                is_complete = chunk.get("is_complete", False)
                is_round_complete = chunk.get("round_complete", False)
                answer = chunk.get("answer", "")

                if speaker and speaker != "Orchestrator":
                    status_placeholder.markdown(
                        f"<div class='orchestrator-status'>"
                        f"<div class='status-dot'></div>{speaker} is thinking...</div>",
                        unsafe_allow_html=True,
                    )

                if is_complete and answer:
                    color = get_persona_color(speaker)
                    with st.chat_message("assistant"):
                        st.markdown(
                            f"<span class='chat-bubble-speaker-label' style='color:{color};'>● {speaker}</span>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(answer)

                    group_history.append({
                        "role": "document",
                        "speaker": speaker,
                        "document_id": chunk.get("document_id"),
                        "content": answer,
                        "web_search_performed": chunk.get("web_search_performed", False),
                    })

                if is_round_complete:
                    status_placeholder.empty()
                    break

            st.session_state.group_chat_history = group_history
            st.rerun()


# ── Entry point: call router after all functions are defined ──
_run_router()

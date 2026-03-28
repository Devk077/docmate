__module_name__ = "styles"

import streamlit as st

# Per-document colour palette (max 10 docs per room)
PERSONA_COLORS = [
    "#5B8AF5",  # blue
    "#F5825B",  # orange
    "#5BF5A0",  # green
    "#F5D65B",  # yellow
    "#C65BF5",  # purple
    "#F55B9D",  # pink
    "#5BDEF5",  # cyan
    "#F55B5B",  # red
    "#8AF55B",  # lime
    "#F5A55B",  # amber
]


def get_persona_color(persona_name: str) -> str:
    """Return a consistent hex colour for a persona name."""
    color_map = st.session_state.get("persona_color_map", {})
    if persona_name not in color_map:
        idx = len(color_map) % len(PERSONA_COLORS)
        color_map[persona_name] = PERSONA_COLORS[idx]
        st.session_state.persona_color_map = color_map
    return color_map[persona_name]


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap');

        /* ── Base ── */
        html, body, [class*="stApp"] {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background-color: #0f1117;
            color: #e2e8f0;
        }

        /* ── Buttons ── */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(91,138,245,0.3);
        }

        /* ── Chat input ── */
        .stChatInput > div {
            border-radius: 12px;
            border: 1px solid #2d3748;
            background: #1a202c;
        }

        /* ── Main title ── */
        h1 {
            font-family: 'Inter', 'Poppins', sans-serif !important;
            font-weight: 700;
            letter-spacing: -0.025em;
        }
        .doqtoq-title {
            font-family: 'Inter', 'Poppins', sans-serif !important;
            font-weight: 700;
            font-size: 2.5rem;
            background: linear-gradient(135deg, #5B8AF5 0%, #C65BF5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.03em;
        }
        .doqtoq-subtitle {
            color: #718096;
            font-size: 1rem;
            margin-top: -0.5rem;
        }

        /* ── Sidebar rooms list ── */
        .room-list-header {
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #718096;
            margin: 16px 0 8px 0;
        }
        .room-card {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 8px;
            margin-bottom: 4px;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.15s ease;
            background: #1a202c;
        }
        .room-card:hover {
            background: #2d3748;
            border-color: #4a5568;
        }
        .room-card.active {
            background: #1e3a5f;
            border-color: #5B8AF5;
        }
        .room-card-name {
            font-weight: 500;
            font-size: 0.9rem;
            color: #e2e8f0;
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .room-card-count {
            font-size: 0.75rem;
            color: #718096;
            background: #2d3748;
            padding: 2px 6px;
            border-radius: 10px;
        }

        /* ── Participant panel ── */
        .participant-panel {
            background: #1a202c;
            border-radius: 12px;
            border: 1px solid #2d3748;
            padding: 16px;
            height: 100%;
        }
        .participant-panel-header {
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #718096;
            margin-bottom: 12px;
        }
        .participant-card {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 8px;
            margin-bottom: 6px;
            background: #131720;
            border: 1px solid #2d3748;
            transition: all 0.2s ease;
        }
        .participant-card:hover {
            border-color: #4a5568;
        }
        .participant-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .participant-dot.active {
            box-shadow: 0 0 6px currentColor;
        }
        .participant-dot.spent {
            opacity: 0.4;
        }
        .participant-name {
            font-weight: 500;
            font-size: 0.9rem;
            color: #e2e8f0;
            flex: 1;
        }
        .participant-status {
            font-size: 0.72rem;
            color: #718096;
        }

        /* ── Chat bubbles (group mode) ── */
        .chat-bubble-group {
            margin: 12px 0;
            animation: fadeInUp 0.3s ease;
        }
        .chat-bubble-speaker-label {
            font-size: 0.78rem;
            font-weight: 600;
            margin-bottom: 4px;
            padding-left: 4px;
        }
        .chat-bubble-content {
            padding: 12px 16px;
            border-radius: 12px;
            border-top-left-radius: 2px;
            font-size: 0.95rem;
            line-height: 1.6;
            max-width: 90%;
        }
        .chat-bubble-user .chat-bubble-content {
            background: #1e3a5f;
            border: 1px solid #2b5297;
            border-radius: 12px;
            border-bottom-right-radius: 2px;
            margin-left: auto;
        }

        /* ── Orchestrator status badge ── */
        .orchestrator-status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            background: #1a202c;
            border: 1px solid #2d3748;
            color: #718096;
            margin: 8px 0;
        }
        .orchestrator-status .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #48BB78;
            animation: pulse 1.5s infinite;
        }

        /* ── Animations ── */
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(8px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0.4; }
        }

        /* ── Home screen room grid ── */
        .home-room-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 24px;
        }
        .home-room-card {
            background: linear-gradient(135deg, #1a202c 0%, #131720 100%);
            border: 1px solid #2d3748;
            border-radius: 16px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .home-room-card:hover {
            border-color: #5B8AF5;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(91,138,245,0.15);
        }
        .home-room-card-title {
            font-weight: 600;
            font-size: 1rem;
            color: #e2e8f0;
            margin-bottom: 6px;
        }
        .home-room-card-meta {
            font-size: 0.8rem;
            color: #718096;
        }

        /* ── New Room button ── */
        .new-room-btn {
            background: linear-gradient(135deg, #5B8AF5 0%, #C65BF5 100%) !important;
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.5rem !important;
        }

        /* ── Scrollbars ── */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 2px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

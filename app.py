"""SlothMate AI - Local-first personal productivity assistant.

Tagline: Work less. Let your local AI handle the boring stuff.
"""
import streamlit as st
from datetime import datetime
from config import config
from storage.database import Database
from ai.local_model import LocalModelService
from services.inbox_processor import InboxProcessor

from ui.dashboard import render_dashboard
from ui.inbox import render_inbox
from ui.briefing import render_briefing
from ui.tasks import render_tasks
from ui.history import render_history
from ui.settings import render_settings

# Configure Streamlit page
st.set_page_config(
    page_title="SlothMate AI | Local Productivity Assistant",
    page_icon="🦥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Calm Forest & Warm Off-White Theme Styling
st.markdown("""
<style>
    /* Main background and base font */
    .stApp {
        background-color: #FAF9F6;
        color: #2D3748;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F1F4EE !important;
        border-right: 1px solid #DCE3D8;
    }

    /* Headings */
    h1, h2, h3, h4 {
        color: #1E3A1A;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* Primary buttons */
    .stButton > button[kind="primary"] {
        background-color: #2D5A27 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #3E7B35 !important;
        box-shadow: 0 4px 12px rgba(45, 90, 39, 0.25) !important;
    }

    /* Secondary buttons */
    .stButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #2D5A27 !important;
        border: 1px solid #C4D4C0 !important;
        border-radius: 8px !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #2D5A27 !important;
        background-color: #F7FAF6 !important;
    }

    /* Card containers */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8DE;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
    }

    /* Tabs styling */
    button[data-baseweb="tab"] {
        font-weight: 600;
        color: #5A6B54;
    }
    button[aria-selected="true"] {
        color: #2D5A27 !important;
        border-bottom-color: #2D5A27 !important;
    }

    /* Subtle divider */
    hr {
        border-color: #E2E8DE;
    }
</style>
""", unsafe_allow_html=True)

# Cache database connection
@st.cache_resource
def get_database():
    return Database(config.db_path)

# Initialize Session State
if "reference_date" not in st.session_state:
    st.session_state["reference_date"] = datetime.now().strftime("%Y-%m-%d")

if "active_nav" not in st.session_state:
    st.session_state["active_nav"] = "Dashboard"

db = get_database()

# Initialize AI Service
active_model = st.session_state.get("active_model", config.default_model)
ollama_url = st.session_state.get("ollama_url", config.ollama_base_url)

ai_service = LocalModelService(
    base_url=ollama_url,
    model_name=active_model,
    timeout=config.request_timeout_seconds,
    temperature=config.temperature
)

# If default model is missing, check if any installed model can be suggested
installed = ai_service.get_installed_models()
if installed and "active_model" not in st.session_state:
    # Prefer qwen2.5:3b if installed, otherwise pick first installed model like llama3.2
    for m in installed:
        if "qwen2.5" in m.lower():
            st.session_state["active_model"] = m
            ai_service.model_name = m
            break
    else:
        st.session_state["active_model"] = installed[0]
        ai_service.model_name = installed[0]

processor = InboxProcessor(
    db=db,
    ai_service=ai_service,
    inbox_dir=config.inbox_dir
)

# ----------------- Sidebar Navigation -----------------
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
            <span style="font-size: 2rem;">🦥</span>
            <div>
                <h2 style="margin: 0; font-size: 1.35rem; color: #1E3A1A;">SlothMate AI</h2>
                <div style="font-size: 0.78rem; color: #5A6B54; line-height: 1.1;">Local-First Assistant</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.caption("Work less. Let local AI handle the boring stuff.")
    st.markdown("<hr style='margin: 10px 0 16px 0;' />", unsafe_allow_html=True)

    # Live AI Status Badge
    ai_status = ai_service.check_status()
    state = ai_status["state"]

    if state == "connected":
        st.markdown(f"""
            <div style="background: #EAF4E8; border: 1px solid #94C78B; border-radius: 6px; padding: 6px 10px; font-size: 0.82rem; margin-bottom: 16px;">
                <span style="color: #23541E; font-weight: 700;">🟢 Connected</span>
                <div style="color: #4A6E46; font-size: 0.75rem; margin-top: 2px;">Model: <code>{ai_service.model_name}</code></div>
            </div>
        """, unsafe_allow_html=True)
    elif state == "model_missing":
        st.markdown(f"""
            <div style="background: #FFF9E6; border: 1px solid #ECC968; border-radius: 6px; padding: 6px 10px; font-size: 0.82rem; margin-bottom: 16px;">
                <span style="color: #8C6207; font-weight: 700;">🟡 Model Missing</span>
                <div style="color: #735105; font-size: 0.75rem; margin-top: 2px;"><code>{ai_status['install_command']}</code></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background: #FDF0ED; border: 1px solid #E8A79B; border-radius: 6px; padding: 6px 10px; font-size: 0.82rem; margin-bottom: 16px;">
                <span style="color: #8C2919; font-weight: 700;">🔴 Ollama Unavailable</span>
                <div style="color: #732215; font-size: 0.75rem; margin-top: 2px;">Start local Ollama server</div>
            </div>
        """, unsafe_allow_html=True)

    # Navigation options
    nav_items = [
        "Dashboard",
        "Lazy Inbox",
        "Morning Briefing",
        "My Tasks",
        "History",
        "Settings"
    ]

    selected_nav = st.radio(
        "Navigation",
        options=nav_items,
        index=nav_items.index(st.session_state["active_nav"]) if st.session_state["active_nav"] in nav_items else 0,
        label_visibility="collapsed"
    )

    if selected_nav != st.session_state["active_nav"]:
        st.session_state["active_nav"] = selected_nav
        st.rerun()

    st.markdown("<hr style='margin: 24px 0 16px 0;' />", unsafe_allow_html=True)
    
    # Quick Sloth Mode from sidebar
    if st.button("⚡ Quick Sloth Mode", use_container_width=True, type="secondary"):
        with st.spinner("Processing inbox..."):
            res = processor.run_sloth_mode(reference_date=st.session_state["reference_date"])
            st.session_state["active_nav"] = "Morning Briefing"
            st.rerun()

    st.markdown("""
        <div style="font-size: 0.75rem; color: #8A9E85; text-align: center; margin-top: 30px;">
            SlothMate AI v1.0.0<br>
            100% Local & Offline-Ready
        </div>
    """, unsafe_allow_html=True)

# ----------------- Main View Routing -----------------
active = st.session_state["active_nav"]

if active == "Dashboard":
    render_dashboard(db, processor)
elif active == "Lazy Inbox":
    render_inbox(db, processor)
elif active == "Morning Briefing":
    render_briefing(db)
elif active == "My Tasks":
    render_tasks(db)
elif active == "History":
    render_history(db)
elif active == "Settings":
    render_settings(db, ai_service)

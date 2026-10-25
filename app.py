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

# Bulletproof High-Contrast Theme: Calm Forest & Warm Off-White
# Completely overrides any browser Dark Mode or Streamlit theme collisions
st.markdown("""
<style>
    /* Global Reset & Strict Contrast Tokens */
    :root, .stApp {
        --text-color: #1E293B !important;
        --primary-color: #2D5A27 !important;
        --background-color: #FAF9F6 !important;
        --secondary-background-color: #F1F4EE !important;
        background-color: #FAF9F6 !important;
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Target all standard text across the app */
    .stApp,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp li,
    .stApp td,
    .stApp th,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] span,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] strong,
    div[data-testid="stMarkdownContainer"] div {
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }

    /* Headings (H1 to H6) */
    h1, h2, h3, h4, h5, h6,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    div[data-testid="stMarkdownContainer"] h4,
    div[data-testid="stMarkdownContainer"] h5,
    div[data-testid="stMarkdownContainer"] h6 {
        color: #1E3A1A !important;
        -webkit-text-fill-color: #1E3A1A !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* Metric Cards - Value (Big numbers e.g. 13, 0, 4) */
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *,
    div[data-testid="stMetricValue"] div,
    div[data-testid="stMetricValue"] span,
    div[data-testid="stMetricValue"] p {
        color: #1E3A1A !important;
        -webkit-text-fill-color: #1E3A1A !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
        opacity: 1 !important;
    }

    /* Metric Cards - Label (Pending Tasks, Completed Tasks, etc.) */
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMetricLabel"] label,
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] span,
    div[data-testid="stMetricLabel"] div {
        color: #2D5A27 !important;
        -webkit-text-fill-color: #2D5A27 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        opacity: 1 !important;
    }

    /* Metric Card Container */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D6E3D1 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 2px 8px rgba(30, 58, 26, 0.05) !important;
    }

    /* Metric Delta */
    div[data-testid="stMetricDelta"] div,
    div[data-testid="stMetricDelta"] span {
        font-weight: 600 !important;
    }

    /* Sidebar Background and Typography */
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"] {
        background-color: #F1F4EE !important;
        border-right: 1px solid #DCE3D8 !important;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2 {
        color: #1E3A1A !important;
        -webkit-text-fill-color: #1E3A1A !important;
    }

    /* Sidebar Radio Navigation items */
    div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"] label,
    div[data-testid="stRadio"] label *,
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] label span,
    div[data-testid="stRadio"] div {
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }

    /* Hover & Active Radio Navigation Item */
    div[data-testid="stRadio"] label:hover p,
    div[data-testid="stRadio"] label:hover span {
        color: #2D5A27 !important;
        -webkit-text-fill-color: #2D5A27 !important;
    }

    div[data-testid="stRadio"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"] label[data-checked="true"] p,
    div[data-testid="stRadio"] label[data-checked="true"] span,
    div[data-testid="stRadio"] label[data-checked="true"] * {
        color: #2D5A27 !important;
        -webkit-text-fill-color: #2D5A27 !important;
        font-weight: 700 !important;
    }

    /* Primary Action Buttons */
    .stButton > button[kind="primary"],
    .stButton > button[kind="primary"] * {
        background-color: #2D5A27 !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        padding: 0.5rem 1.2rem !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #3E7B35 !important;
        box-shadow: 0 4px 12px rgba(45, 90, 39, 0.25) !important;
    }

    /* Secondary Action Buttons */
    .stButton > button[kind="secondary"],
    .stButton > button[kind="secondary"] * {
        background-color: #FFFFFF !important;
        color: #2D5A27 !important;
        -webkit-text-fill-color: #2D5A27 !important;
        border: 1px solid #C4D4C0 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #2D5A27 !important;
        background-color: #F7FAF6 !important;
    }

    /* Form Inputs, Dropdowns, Textareas */
    input, textarea, select,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        color: #0F172A !important;
        -webkit-text-fill-color: #0F172A !important;
        background-color: #FFFFFF !important;
        border: 1px solid #C4D4C0 !important;
    }

    div[data-baseweb="select"] *,
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"] * {
        color: #0F172A !important;
        -webkit-text-fill-color: #0F172A !important;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D6E3D1 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary *,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {
        color: #1E3A1A !important;
        -webkit-text-fill-color: #1E3A1A !important;
        font-weight: 600 !important;
    }

    /* Tabs */
    button[data-baseweb="tab"] * {
        font-weight: 600 !important;
        color: #4A6346 !important;
        -webkit-text-fill-color: #4A6346 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] * {
        color: #2D5A27 !important;
        -webkit-text-fill-color: #2D5A27 !important;
        font-weight: 700 !important;
    }

    /* Checkboxes */
    [data-testid="stCheckbox"] label span,
    [data-testid="stCheckbox"] label p {
        color: #1E293B !important;
        -webkit-text-fill-color: #1E293B !important;
    }

    /* Captions & subtle text */
    [data-testid="stCaptionContainer"] p,
    .stCaption,
    small {
        color: #4A6346 !important;
        -webkit-text-fill-color: #4A6346 !important;
    }

    /* Horizontal Rules */
    hr {
        border-color: #E2E8DE !important;
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
            <span style="font-size: 2.2rem;">🦥</span>
            <div>
                <h2 style="margin: 0; font-size: 1.4rem; color: #1E3A1A !important; font-weight: 700;">SlothMate AI</h2>
                <div style="font-size: 0.8rem; color: #385233 !important; font-weight: 600;">Local-First Assistant</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='font-size: 0.82rem; color: #4A6346 !important; margin: 0 0 12px 0;'>Work less. Let local AI handle the boring stuff.</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 4px 0 16px 0;' />", unsafe_allow_html=True)

    # Live AI Status Badge
    ai_status = ai_service.check_status()
    state = ai_status["state"]

    if state == "connected":
        st.markdown(f"""
            <div style="background: #EAF4E8; border: 1px solid #94C78B; border-radius: 6px; padding: 8px 12px; font-size: 0.85rem; margin-bottom: 16px;">
                <span style="color: #23541E !important; font-weight: 700;">🟢 Connected</span>
                <div style="color: #2D4F2A !important; font-size: 0.78rem; margin-top: 2px;">Model: <code style="color: #1E3A1A !important; background: #D5E8D2;">{ai_service.model_name}</code></div>
            </div>
        """, unsafe_allow_html=True)
    elif state == "model_missing":
        st.markdown(f"""
            <div style="background: #FFF9E6; border: 1px solid #ECC968; border-radius: 6px; padding: 8px 12px; font-size: 0.85rem; margin-bottom: 16px;">
                <span style="color: #8C6207 !important; font-weight: 700;">🟡 Model Missing</span>
                <div style="color: #634604 !important; font-size: 0.78rem; margin-top: 2px;"><code style="color: #634604 !important; background: #FCE8B3;">{ai_status['install_command']}</code></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background: #FDF0ED; border: 1px solid #E8A79B; border-radius: 6px; padding: 8px 12px; font-size: 0.85rem; margin-bottom: 16px;">
                <span style="color: #8C2919 !important; font-weight: 700;">🔴 Ollama Unavailable</span>
                <div style="color: #611D12 !important; font-size: 0.78rem; margin-top: 2px;">Start local Ollama server</div>
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
        <div style="font-size: 0.75rem; color: #556B4F !important; text-align: center; margin-top: 30px;">
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

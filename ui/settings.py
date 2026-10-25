"""Settings and Configuration interface for SlothMate AI."""
import streamlit as st
from pathlib import Path
from storage.database import Database
from ai.local_model import LocalModelService
from config import config

def render_settings(db: Database, ai_service: LocalModelService):
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1E3A1A;">⚙️ Settings & System Health</h2>
            <p style="margin: 4px 0 0 0; color: #5A6B54;">
                Manage local Ollama model settings, directory paths, and privacy controls.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 1. Local AI Configuration Section
    st.markdown("### 🤖 Local AI Model Settings")

    col_url, col_model = st.columns(2)
    with col_url:
        base_url = st.text_input(
            "Ollama Base URL",
            value=st.session_state.get("ollama_url", config.ollama_base_url),
            help="Local endpoint where your Ollama server is running."
        )
        if base_url != st.session_state.get("ollama_url"):
            st.session_state["ollama_url"] = base_url
            ai_service.base_url = base_url.rstrip("/")

    # Detect installed models
    installed_models = ai_service.get_installed_models()

    with col_model:
        current_model = st.session_state.get("active_model", config.default_model)
        
        # Build options including installed models and default
        options = []
        if config.default_model not in options:
            options.append(config.default_model)
        for im in installed_models:
            if im not in options:
                options.append(im)
        options.append("Custom model name...")

        default_idx = options.index(current_model) if current_model in options else 0
        selected_option = st.selectbox(
            "Configured Model",
            options=options,
            index=default_idx,
            help="Choose an installed Ollama model or enter a custom model tag."
        )

        if selected_option == "Custom model name...":
            custom_model = st.text_input("Enter custom model tag", value=current_model)
            model_to_use = custom_model.strip()
        else:
            model_to_use = selected_option

        if model_to_use != st.session_state.get("active_model"):
            st.session_state["active_model"] = model_to_use
            ai_service.model_name = model_to_use
            st.rerun()

    # Temperature & Timeout
    col_temp, col_timeout = st.columns(2)
    with col_temp:
        temp = st.slider("Temperature (lower = more deterministic)", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
        ai_service.temperature = temp

    with col_timeout:
        timeout = st.slider("Request Timeout (seconds)", min_value=15, max_value=300, value=60, step=15)
        ai_service.timeout = timeout

    # Live Connection Status Box
    st.markdown("#### AI Status Indicator")
    status = ai_service.check_status()

    if status["state"] == "connected":
        st.markdown(f"""
            <div style="background: #EAF4E8; border: 1px solid #94C78B; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="color: #23541E; font-weight: 700; font-size: 1.05rem;">
                    🟢 Connected — Model Available & Offline-Ready
                </div>
                <div style="color: #3B6B36; font-size: 0.95rem; margin-top: 4px;">
                    {status['message']}
                </div>
            </div>
        """, unsafe_allow_html=True)
    elif status["state"] == "model_missing":
        st.markdown(f"""
            <div style="background: #FFF9E6; border: 1px solid #ECC968; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="color: #8C6207; font-weight: 700; font-size: 1.05rem;">
                    🟡 Model Missing — Installation Required
                </div>
                <div style="color: #735105; font-size: 0.95rem; margin-top: 4px;">
                    {status['message']}
                </div>
                <div style="margin-top: 8px; font-family: monospace; background: #FFFFFF; padding: 6px 12px; border-radius: 4px; display: inline-block;">
                    {status['install_command']}
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="background: #FDF0ED; border: 1px solid #E8A79B; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;">
                <div style="color: #8C2919; font-weight: 700; font-size: 1.05rem;">
                    🔴 Ollama Unavailable — Service Not Running
                </div>
                <div style="color: #732215; font-size: 0.95rem; margin-top: 4px;">
                    {status['message']}
                </div>
                <div style="margin-top: 8px; font-family: monospace; background: #FFFFFF; padding: 6px 12px; border-radius: 4px; display: inline-block;">
                    ollama serve
                </div>
            </div>
        """, unsafe_allow_html=True)

    if installed_models:
        st.caption(f"Installed models detected on your system: `{', '.join(installed_models)}`")

    st.markdown("<hr style='margin: 24px 0; border: none; border-top: 1px solid #E2E8DE;' />", unsafe_allow_html=True)

    # 2. Storage & Privacy Controls
    st.markdown("### 🔒 Privacy & Data Management")
    st.markdown("""
        SlothMate operates on local-first principles:
        - All database records (`slothmate.db`) are stored locally.
        - Document text is never uploaded to external clouds or third-party APIs.
        - No telemetry or analytics are collected.
    """)

    st.markdown(f"**Database location:** `{config.db_path.resolve()}`")
    st.markdown(f"**Inbox location:** `{config.inbox_dir.resolve()}`")

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚠️ Danger Zone: Reset Database Data", expanded=False):
        st.warning("This will permanently delete all parsed documents, tasks, and historical briefings from the local SQLite database. Files inside your inbox directory will not be deleted.")
        confirm = st.checkbox("Yes, I understand and want to wipe all local task and briefing history.")
        if st.button("🗑️ Reset Database", type="secondary", disabled=not confirm):
            db.reset_database()
            st.success("Database has been reset to an empty state.")
            st.rerun()

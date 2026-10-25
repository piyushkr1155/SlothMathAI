"""Dashboard view for SlothMate AI."""
import streamlit as st
from datetime import datetime
from storage.database import Database
from services.inbox_processor import InboxProcessor

def render_dashboard(db: Database, processor: InboxProcessor):
    st.markdown("""
        <div style="margin-bottom: 24px;">
            <h1 style="margin: 0; font-size: 2.2rem; color: #1E3A1A; font-weight: 700;">
                🦥 SlothMate AI
            </h1>
            <p style="margin: 4px 0 0 0; color: #5A6B54; font-size: 1.05rem;">
                Work less. Let your local AI handle the boring stuff.
            </p>
        </div>
    """, unsafe_allow_html=True)

    ref_date = st.session_state.get("reference_date", datetime.now().strftime("%Y-%m-%d"))
    metrics = db.get_metrics(reference_date=ref_date)

    # 4 Key Metrics Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Pending Tasks",
            value=metrics["pending_tasks"],
            delta=f"{metrics['due_today_tasks']} due today" if metrics['due_today_tasks'] > 0 else None,
            delta_color="off"
        )
    with col2:
        st.metric(
            label="Completed Tasks",
            value=metrics["completed_tasks"],
            delta="In progress: " + str(metrics["in_progress_tasks"]),
            delta_color="normal"
        )
    with col3:
        st.metric(
            label="Overdue Tasks",
            value=metrics["overdue_tasks"],
            delta="Requires attention" if metrics["overdue_tasks"] > 0 else "All on track",
            delta_color="inverse" if metrics["overdue_tasks"] > 0 else "normal"
        )
    with col4:
        st.metric(
            label="Documents Processed",
            value=metrics["processed_docs"],
            delta=f"{metrics['pending_docs']} waiting in inbox",
            delta_color="off"
        )

    st.markdown("<hr style='margin: 28px 0; border: none; border-top: 1px solid #E2E8DE;' />", unsafe_allow_html=True)

    # Sloth Mode Hero Action Box
    st.markdown("""
        <div style="background: #F4F7F2; border: 1px solid #D6E3D1; border-radius: 12px; padding: 22px; margin-bottom: 24px;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h3 style="margin: 0 0 6px 0; color: #23451F; font-size: 1.3rem;">
                        ⚡ Sloth Mode
                    </h3>
                    <p style="margin: 0; color: #4F634A; font-size: 0.95rem;">
                        Scan your inbox, summarize new files, extract deadlines, and generate today's briefing in one click.
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Check candidate files in inbox
    inbox_files = processor.scan_inbox()
    eligible_count = len(inbox_files)

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        run_clicked = st.button("🦥 Run Sloth Mode", type="primary", use_container_width=True)
    with col_info:
        st.caption(f"📁 **{eligible_count} supported document(s)** found in inbox directory (`{processor.inbox_dir.name}`).")

    # Run Sloth Mode Execution
    if run_clicked:
        if eligible_count == 0:
            st.info("Your inbox is empty! Upload documents in the **Lazy Inbox** tab or place files in your inbox folder.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_cb(current, total, filename, msg):
                pct = int((current / max(total, 1)) * 100)
                progress_bar.progress(pct)
                status_text.text(f"[{current}/{total}] {filename}: {msg}")

            with st.spinner("Sloth is at work... reading documents and synthesizing briefing..."):
                results = processor.run_sloth_mode(
                    reference_date=ref_date,
                    progress_callback=progress_cb
                )

            progress_bar.empty()
            status_text.empty()

            st.success(
                f"🎉 **Sloth Mode Complete!** "
                f"Processed: {len(results['successes'])}, "
                f"Skipped (unchanged): {len(results['skipped'])}, "
                f"Failures: {len(results['failures'])}, "
                f"New Tasks: {results['new_tasks_count']}."
            )

            if results["failures"]:
                with st.expander("⚠️ View Processing Warnings / Failures", expanded=True):
                    for f in results["failures"]:
                        st.error(f"**{f['filename']}**: {f.get('error')}")

            # Switch to briefing tab
            st.session_state["active_nav"] = "Morning Briefing"
            st.rerun()

    # Latest Briefing Summary & Quick Tasks
    latest_briefing = db.get_latest_briefing()
    st.markdown("### 📋 Latest Morning Briefing Highlight")

    if latest_briefing:
        col_b1, col_b2 = st.columns([1.6, 1])
        with col_b1:
            st.markdown(f"**Generated for:** `{latest_briefing.get('reference_date')}`")
            st.markdown(f"> {latest_briefing.get('executive_summary', 'No summary available.')}")
            
            top_p = latest_briefing.get("top_priorities", [])
            if top_p:
                st.markdown("**Top Priorities:**")
                for i, p in enumerate(top_p[:3], 1):
                    st.markdown(f"{i}. {p}")
        
        with col_b2:
            st.markdown("**Tasks Due Today:**")
            due_today = latest_briefing.get("tasks_due_today", [])
            if due_today:
                for dt in due_today[:5]:
                    st.markdown(f"- ⏳ {dt}")
            else:
                st.info("No urgent tasks due today!")

            if st.button("View Full Briefing & Export ➔", use_container_width=True):
                st.session_state["active_nav"] = "Morning Briefing"
                st.rerun()
    else:
        st.info("No briefings generated yet. Run **Sloth Mode** above or import documents in **Lazy Inbox** to generate your first briefing.")

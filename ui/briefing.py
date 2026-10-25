"""Morning Briefing viewer and export interface for SlothMate AI."""
import streamlit as st
from datetime import datetime, date
from storage.database import Database
from services.briefing import consolidate_briefing

def render_briefing(db: Database):
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1E3A1A;">🌅 Morning Briefing</h2>
            <p style="margin: 4px 0 0 0; color: #5A6B54;">
                Consolidated daily intelligence, decisions, and deadlines synthesized from all your inbox documents.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Reference Date Picker & Actions Bar
    col_date, col_regen, col_export = st.columns([1.5, 1, 1.2])
    with col_date:
        current_ref = st.session_state.get("reference_date", datetime.now().strftime("%Y-%m-%d"))
        try:
            parsed_d = datetime.strptime(current_ref, "%Y-%m-%d").date()
        except Exception:
            parsed_d = date.today()

        picked_date = st.date_input("Reference Date", value=parsed_d, help="Used for testing and date-sensitive deadline matching.")
        picked_str = picked_date.strftime("%Y-%m-%d")
        if picked_str != current_ref:
            st.session_state["reference_date"] = picked_str
            st.rerun()

    with col_regen:
        st.write("") # spacer
        st.write("")
        if st.button("🔄 Re-synthesize", use_container_width=True, help="Re-consolidate active documents with current reference date"):
            with st.spinner("Consolidating documents..."):
                active_docs = db.list_documents(status="processed")
                active_tasks = db.list_tasks(status="pending")
                briefing_data = consolidate_briefing(
                    documents=active_docs,
                    tasks=active_tasks,
                    reference_date=picked_str
                )
                db.save_briefing(briefing_data)
                st.success("Briefing updated!")
                st.rerun()

    latest_briefing = db.get_latest_briefing()
    if not latest_briefing:
        st.info("No briefing generated yet. Run **Sloth Mode** on the Dashboard to synthesize your inbox documents.")
        return

    md_content = latest_briefing.get("markdown_content", "")
    with col_export:
        st.write("") # spacer
        st.write("")
        st.download_button(
            label="📥 Export Briefing (.md)",
            data=md_content,
            file_name=f"slothmate_briefing_{picked_str}.md",
            mime="text/markdown",
            use_container_width=True
        )

    st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #E2E8DE;' />", unsafe_allow_html=True)

    # Render structured sections
    tab_formatted, tab_markdown = st.tabs(["📑 Consolidated View", "📝 Raw Markdown"])

    with tab_formatted:
        # Executive Summary Box
        st.markdown("""
            <div style="background: #F4F7F2; border-left: 4px solid #3E7B35; border-radius: 6px; padding: 14px 18px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 6px 0; color: #1E3A1A;">🧭 Executive Summary</h4>
                <div style="color: #2E3E2A; font-size: 1.05rem; line-height: 1.5;">
        """ + (latest_briefing.get("executive_summary") or "No summary available.") + """
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Top Three Priorities
        st.markdown("### 🎯 Top Three Priorities")
        top_p = latest_briefing.get("top_priorities", [])
        if top_p:
            for i, p in enumerate(top_p[:3], 1):
                st.markdown(f"""
                    <div style="background: #FFFFFF; border: 1px solid #D6E3D1; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                        <span style="font-weight: 700; color: #2D5A27; font-size: 1.1rem; margin-right: 8px;">#{i}</span>
                        <span style="font-size: 1rem; color: #1F2937;">{p}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No top priorities recorded.")

        st.markdown("<br>", unsafe_allow_html=True)

        # 2-column layout for Tasks Due Today & Upcoming Deadlines
        col_due, col_up = st.columns(2)
        with col_due:
            st.markdown(f"### 📅 Tasks Due Today ({picked_str})")
            due_tasks = latest_briefing.get("tasks_due_today", [])
            if due_tasks:
                for dt in due_tasks:
                    st.markdown(f"- ⏳ **{dt}**")
            else:
                st.success("✅ No tasks due today. Steady pace!")

        with col_up:
            st.markdown("### ⏳ Upcoming Deadlines")
            up_deadlines = latest_briefing.get("upcoming_deadlines", [])
            if up_deadlines:
                for ud in up_deadlines:
                    st.markdown(f"- 📌 {ud}")
            else:
                st.caption("No explicit upcoming deadlines logged.")

        st.markdown("<hr style='margin: 20px 0; border: none; border-top: 1px solid #E2E8DE;' />", unsafe_allow_html=True)

        # Decisions & Follow-ups
        col_dec, col_fol = st.columns(2)
        with col_dec:
            st.markdown("### 💡 Key Decisions")
            decisions = latest_briefing.get("decisions", [])
            if decisions:
                for dec in decisions:
                    st.markdown(f"- {dec}")
            else:
                st.caption("No key decisions noted.")

        with col_fol:
            st.markdown("### 📬 Follow-Up Items")
            follow_ups = latest_briefing.get("follow_ups", [])
            if follow_ups:
                for fol in follow_ups:
                    st.markdown(f"- 💬 {fol}")
            else:
                st.caption("No follow-up items recorded.")

        st.markdown("<hr style='margin: 20px 0; border: none; border-top: 1px solid #E2E8DE;' />", unsafe_allow_html=True)

        # Can Wait & Uncertainties
        col_wait, col_unc = st.columns(2)
        with col_wait:
            st.markdown("### 💤 Can Safely Wait (Low Priority)")
            can_wait = latest_briefing.get("can_wait", [])
            if can_wait:
                for cw in can_wait:
                    st.markdown(f"- 🦥 {cw}")
            else:
                st.caption("No low-priority deferred items.")

        with col_unc:
            st.markdown("### ❓ Uncertainties (Verification Needed)")
            uncertainties = latest_briefing.get("uncertainties", [])
            if uncertainties:
                for un in uncertainties:
                    st.markdown(f"- ⚠️ **{un}**")
            else:
                st.caption("All extracted data is clear and unambiguous.")

        # Source Documents Footer
        st.markdown("### 📂 Source Documents Analyzed")
        source_docs = latest_briefing.get("source_documents", [])
        if source_docs:
            st.markdown(" ".join([f"`{doc}`" for doc in source_docs]))
        else:
            st.caption("None.")

    with tab_markdown:
        st.text_area("Markdown Source", value=md_content, height=450)

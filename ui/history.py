"""History and Archive view for SlothMate AI."""
import streamlit as st
from storage.database import Database

def render_history(db: Database):
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1E3A1A;">📜 History & Runs</h2>
            <p style="margin: 4px 0 0 0; color: #5A6B54;">
                Browse historical briefings, past summaries, and Sloth Mode run logs.
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab_briefings, tab_runs = st.tabs(["📑 Past Briefings", "⚙️ Sloth Mode Run Logs"])

    with tab_briefings:
        briefings = db.list_briefings(limit=30)
        if not briefings:
            st.info("No historical briefings found.")
        else:
            for b in briefings:
                ref_d = b.get("reference_date", "N/A")
                created = b.get("created_at", "N/A")
                summary_snip = (b.get("executive_summary") or "")[:180] + "..."
                md_content = b.get("markdown_content", "")

                with st.expander(f"📅 Briefing for {ref_d} (Generated: {created})"):
                    st.markdown(f"**Executive Summary:** {b.get('executive_summary')}")
                    
                    st.download_button(
                        label="📥 Download this Briefing (.md)",
                        data=md_content,
                        file_name=f"slothmate_briefing_{ref_d}.md",
                        mime="text/markdown",
                        key=f"dl_hist_{b['id']}"
                    )
                    st.markdown("---")
                    st.markdown(md_content)

    with tab_runs:
        runs = db.list_processing_runs(limit=30)
        if not runs:
            st.info("No processing runs recorded yet.")
        else:
            for r in runs:
                run_at = r.get("run_at", "")[:19].replace("T", " ")
                docs_count = r.get("documents_count", 0)
                tasks_count = r.get("tasks_extracted_count", 0)
                succ = r.get("success_count", 0)
                fail = r.get("failure_count", 0)
                skip = r.get("skipped_count", 0)

                with st.expander(f"⚡ Run at {run_at} — {succ} succeeded, {skip} skipped, {fail} failed ({tasks_count} new tasks)"):
                    st.markdown(f"- **Total Candidate Files:** {docs_count}")
                    st.markdown(f"- **Successes:** {succ}")
                    st.markdown(f"- **Skipped (Identical Hash):** {skip}")
                    st.markdown(f"- **Failures:** {fail}")
                    st.markdown(f"- **New Tasks Extracted:** {tasks_count}")

                    details = r.get("details")
                    if details and isinstance(details, dict):
                        if details.get("successes"):
                            st.markdown(f"**Processed Files:** `{'`, `'.join(details['successes'])}`")
                        if details.get("failures"):
                            st.error(f"**Failures Detail:** {details['failures']}")

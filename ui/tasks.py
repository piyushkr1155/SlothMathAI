"""Task Dashboard ("My Tasks") view for SlothMate AI."""
import streamlit as st
from datetime import datetime
from storage.database import Database

def render_tasks(db: Database):
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1E3A1A;">✅ My Tasks</h2>
            <p style="margin: 4px 0 0 0; color: #5A6B54;">
                Review, filter, and track actionable items extracted from your documents.
            </p>
        </div>
    """, unsafe_allow_html=True)

    ref_date = st.session_state.get("reference_date", datetime.now().strftime("%Y-%m-%d"))

    # Filters Bar
    col_status, col_prio, col_search = st.columns([1.2, 1.2, 2])
    with col_status:
        status_filter = st.selectbox(
            "Status",
            options=["pending", "in_progress", "completed", "dismissed", "all"],
            index=0,
            format_func=lambda x: {
                "pending": "⏳ Pending",
                "in_progress": "🔄 In Progress",
                "completed": "✅ Completed",
                "dismissed": "❌ Dismissed",
                "all": "All Statuses"
            }.get(x, x)
        )
    with col_prio:
        priority_filter = st.selectbox(
            "Priority",
            options=["all", "high", "medium", "low"],
            index=0,
            format_func=lambda x: {
                "all": "All Priorities",
                "high": "🔴 High",
                "medium": "🟡 Medium",
                "low": "🟢 Low"
            }.get(x, x)
        )
    with col_search:
        search_query = st.text_input("Search tasks or source files", placeholder="Type keywords...")

    # Fetch filtered tasks
    tasks = db.list_tasks(
        status=status_filter if status_filter != "all" else None,
        priority=priority_filter if priority_filter != "all" else None,
        search=search_query
    )

    st.caption(f"Showing **{len(tasks)}** task(s) matching your criteria.")

    if not tasks:
        st.info("No tasks found. Try adjusting filters or run **Sloth Mode** to extract action items from inbox documents.")
        return

    st.markdown("<hr style='margin: 12px 0 20px 0; border: none; border-top: 1px solid #E2E8DE;' />", unsafe_allow_html=True)

    # Render Task Cards
    for task in tasks:
        task_id = task["id"]
        priority = task.get("priority", "medium").lower()
        status = task.get("status", "pending")
        deadline = task.get("deadline")

        # Visual styling based on priority
        prio_color = {
            "high": "#D9381E",
            "medium": "#C2820A",
            "low": "#3E7B35"
        }.get(priority, "#5A6B54")

        # Deadline badge
        if deadline:
            if deadline < ref_date and status in ("pending", "in_progress"):
                deadline_badge = f"<span style='color: #D9381E; font-weight: 700;'>⚠️ Overdue: {deadline}</span>"
            elif deadline == ref_date and status in ("pending", "in_progress"):
                deadline_badge = f"<span style='color: #C2820A; font-weight: 700;'>⏳ Due Today: {deadline}</span>"
            else:
                deadline_badge = f"<span style='color: #5A6B54;'>📅 Due: {deadline}</span>"
        else:
            deadline_badge = "<span style='color: #8C9E87;'>No deadline</span>"

        with st.container():
            col_check, col_details, col_actions = st.columns([0.6, 3.2, 1.6])
            
            with col_check:
                is_completed = (status == "completed")
                checked = st.checkbox("Done", value=is_completed, key=f"chk_{task_id}", label_visibility="collapsed")
                if checked != is_completed:
                    new_st = "completed" if checked else "pending"
                    db.update_task(task_id, {"status": new_st})
                    st.rerun()

            with col_details:
                title_style = "text-decoration: line-through; color: #8C9E87;" if is_completed else "color: #1F2937; font-weight: 600;"
                st.markdown(f"<div style='font-size: 1.05rem; {title_style}'>{task['title']}</div>", unsafe_allow_html=True)
                
                # Meta line
                st.markdown(
                    f"<div style='font-size: 0.85rem; margin-top: 4px;'>"
                    f"<span style='color: {prio_color}; font-weight: 700;'>[{priority.upper()}]</span> &nbsp;•&nbsp; "
                    f"{deadline_badge} &nbsp;•&nbsp; "
                    f"📁 <code>{task['source_file']}</code>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                if task.get("evidence"):
                    with st.expander("🔍 View Source Evidence / Quote"):
                        st.markdown(f"_{task['evidence']}_")

            with col_actions:
                # Priority / Status editor popup or buttons
                col_st, col_del = st.columns(2)
                with col_st:
                    status_options = ["pending", "in_progress", "completed", "dismissed"]
                    new_status = st.selectbox(
                        "Status",
                        options=status_options,
                        index=status_options.index(status) if status in status_options else 0,
                        key=f"st_sel_{task_id}",
                        label_visibility="collapsed"
                    )
                    if new_status != status:
                        db.update_task(task_id, {"status": new_status})
                        st.rerun()

                with col_del:
                    if st.button("🗑️", key=f"del_t_{task_id}", help="Delete task permanently"):
                        db.delete_task(task_id)
                        st.rerun()

            st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px dashed #E2E8DE;' />", unsafe_allow_html=True)

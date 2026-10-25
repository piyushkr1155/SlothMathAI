"""Briefing generation and markdown export service for SlothMate AI."""
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

def format_briefing_markdown(briefing: Dict[str, Any]) -> str:
    """Format structured briefing data into clean, readable Markdown."""
    ref_date = briefing.get("reference_date", datetime.now().strftime("%Y-%m-%d"))
    created_at = briefing.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    lines = [
        f"# 🦥 SlothMate AI — Daily Briefing",
        f"**Reference Date:** `{ref_date}` | **Generated:** `{created_at}`",
        "",
        "---",
        "",
        "## 🧭 Executive Summary",
        briefing.get("executive_summary") or "No executive summary available.",
        "",
        "## 🎯 Top Three Priorities",
    ]

    top_priorities = briefing.get("top_priorities", [])
    if top_priorities:
        for i, p in enumerate(top_priorities[:3], 1):
            lines.append(f"{i}. **{p}**")
    else:
        lines.append("_No critical top priorities identified._")

    lines.extend([
        "",
        "## 📅 Tasks Due Today",
    ])
    due_today = briefing.get("tasks_due_today", [])
    if due_today:
        for t in due_today:
            lines.append(f"- [ ] {t}")
    else:
        lines.append("_No tasks due today. Steady pace!_")

    lines.extend([
        "",
        "## ⏳ Upcoming Deadlines",
    ])
    upcoming = briefing.get("upcoming_deadlines", [])
    if upcoming:
        for u in upcoming:
            lines.append(f"- {u}")
    else:
        lines.append("_No upcoming deadlines logged._")

    lines.extend([
        "",
        "## 💡 Key Decisions",
    ])
    decisions = briefing.get("decisions", [])
    if decisions:
        for d in decisions:
            lines.append(f"- {d}")
    else:
        lines.append("_No major decisions noted._")

    lines.extend([
        "",
        "## 📬 Follow-Up Items",
    ])
    follow_ups = briefing.get("follow_ups", [])
    if follow_ups:
        for f in follow_ups:
            lines.append(f"- {f}")
    else:
        lines.append("_None._")

    lines.extend([
        "",
        "## 💤 Can Safely Wait (Low Priority)",
    ])
    can_wait = briefing.get("can_wait", [])
    if can_wait:
        for cw in can_wait:
            lines.append(f"- {cw}")
    else:
        lines.append("_No low-priority deferred items._")

    lines.extend([
        "",
        "## ❓ Uncertainties (Requires Human Verification)",
    ])
    uncertainties = briefing.get("uncertainties", [])
    if uncertainties:
        for un in uncertainties:
            lines.append(f"- ⚠️ {un}")
    else:
        lines.append("_All extracted data is clear and unambiguous._")

    lines.extend([
        "",
        "## 📂 Source Documents",
    ])
    docs = briefing.get("source_documents", [])
    if docs:
        for doc in docs:
            lines.append(f"- `{doc}`")
    else:
        lines.append("_None._")

    lines.extend([
        "",
        "---",
        "_Generated locally and privately by SlothMate AI. No cloud inference used._"
    ])

    return "\n".join(lines)

def consolidate_briefing(
    documents: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    reference_date: Optional[str] = None,
    ai_service = None
) -> Dict[str, Any]:
    """Consolidate document summaries and tasks into a structured briefing dictionary.
    
    Uses deterministic Python consolidation by default, and optionally enhances with local AI if available.
    """
    if reference_date is None:
        reference_date = datetime.now().strftime("%Y-%m-%d")

    # Group tasks by deadline & priority
    tasks_due_today = []
    upcoming_deadlines = []
    can_wait = []
    priorities_pool = []

    for t in tasks:
        title = t.get("title", "")
        deadline = t.get("deadline")
        priority = t.get("priority", "medium").lower()
        src = t.get("source_file", "")
        formatted_entry = f"{title} (Source: {src})" if src else title

        if priority == "high":
            priorities_pool.append(formatted_entry)
        elif priority == "low":
            can_wait.append(formatted_entry)

        if deadline:
            if deadline == reference_date or deadline < reference_date:
                tasks_due_today.append(f"{title} (Due: {deadline}, Priority: {priority})")
            else:
                upcoming_deadlines.append(f"**{deadline}**: {title} [{priority.upper()}] (Source: {src})")

    # If priorities pool < 3, fill with medium priority items with deadlines
    if len(priorities_pool) < 3:
        for t in tasks:
            title = t.get("title", "")
            if t.get("priority") == "medium" and title not in priorities_pool:
                priorities_pool.append(title)
                if len(priorities_pool) >= 3:
                    break

    top_3_priorities = priorities_pool[:3]

    # Consolidate key points, decisions, follow_ups, uncertainties from documents
    all_decisions = []
    all_follow_ups = []
    all_uncertainties = []
    source_documents = []
    summary_snippets = []

    for d in documents:
        fname = d.get("filename", "")
        if fname and fname not in source_documents:
            source_documents.append(fname)

        if d.get("summary"):
            summary_snippets.append(f"[{fname}] {d['summary']}")

        # Extract JSON-stored or list-stored fields
        for field, target_list in [
            ("key_points", all_decisions),
            ("follow_ups", all_follow_ups),
            ("uncertainties", all_uncertainties)
        ]:
            val = d.get(field)
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    val = [val] if val else []
            if isinstance(val, list):
                for item in val:
                    if item and item not in target_list:
                        target_list.append(f"{item} ({fname})")

    # Build executive summary
    if summary_snippets:
        exec_summary = " ".join(summary_snippets)
    else:
        exec_summary = (
            f"Processed {len(documents)} document(s) with {len(tasks)} extracted task(s). "
            f"There are {len(tasks_due_today)} task(s) requiring attention today."
        )

    briefing_dict = {
        "reference_date": reference_date,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "executive_summary": exec_summary,
        "top_priorities": top_3_priorities,
        "tasks_due_today": tasks_due_today,
        "upcoming_deadlines": upcoming_deadlines,
        "decisions": all_decisions[:10],
        "follow_ups": all_follow_ups[:10],
        "can_wait": can_wait[:10],
        "uncertainties": all_uncertainties,
        "source_documents": source_documents,
    }

    # Format Markdown
    briefing_dict["markdown_content"] = format_briefing_markdown(briefing_dict)
    return briefing_dict

"""Tests for briefing consolidation and markdown rendering."""
import pytest
from services.briefing import consolidate_briefing, format_briefing_markdown

def test_consolidate_briefing():
    docs = [
        {
            "filename": "meeting.md",
            "summary": "Reviewed Q4 targets and approved the database migration.",
            "key_points": ["Approved migration", "Postponed analytics"],
            "follow_ups": ["Check with security team"],
            "uncertainties": ["Ambiguous deadline for redesign"]
        }
    ]

    tasks = [
        {
            "title": "Deploy database patch",
            "priority": "high",
            "deadline": "2026-10-25", # due today
            "source_file": "meeting.md"
        },
        {
            "title": "Complete UX wireframes",
            "priority": "medium",
            "deadline": "2026-11-05", # upcoming
            "source_file": "meeting.md"
        },
        {
            "title": "Clean up typography",
            "priority": "low",
            "deadline": None,
            "source_file": "meeting.md"
        }
    ]

    b = consolidate_briefing(docs, tasks, reference_date="2026-10-25")
    
    assert b["reference_date"] == "2026-10-25"
    assert "Reviewed Q4 targets" in b["executive_summary"]
    assert len(b["top_priorities"]) >= 1
    assert any("Deploy database patch" in p for p in b["top_priorities"])
    assert len(b["tasks_due_today"]) == 1
    assert "Deploy database patch" in b["tasks_due_today"][0]
    assert len(b["upcoming_deadlines"]) == 1
    assert "2026-11-05" in b["upcoming_deadlines"][0]
    assert len(b["can_wait"]) == 1
    assert "Clean up typography" in b["can_wait"][0]
    assert "meeting.md" in b["source_documents"]

def test_format_briefing_markdown():
    briefing_data = {
        "reference_date": "2026-10-25",
        "created_at": "2026-10-25 12:00:00",
        "executive_summary": "All systems steady.",
        "top_priorities": ["Priority One", "Priority Two"],
        "tasks_due_today": ["Submit timesheet"],
        "upcoming_deadlines": ["2026-11-01: Launch v1"],
        "decisions": ["Proceed with local SQLite"],
        "follow_ups": ["Confirm license"],
        "can_wait": ["Update colors"],
        "uncertainties": ["Budget pending"],
        "source_documents": ["notes.txt"]
    }

    md = format_briefing_markdown(briefing_data)
    assert "# 🦥 SlothMate AI — Daily Briefing" in md
    assert "All systems steady." in md
    assert "**Priority One**" in md
    assert "Submit timesheet" in md
    assert "Launch v1" in md
    assert "notes.txt" in md

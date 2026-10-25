"""Tests for task extraction, deadline validation, and deduplication."""
import pytest
from services.task_extractor import (
    validate_and_clean_deadline,
    sanitize_task,
    deduplicate_tasks,
    normalize_title
)

def test_explicit_deadlines():
    # ISO formats
    d, unc = validate_and_clean_deadline("2026-10-31")
    assert d == "2026-10-31"
    assert unc is None

    # Month day format
    d, unc = validate_and_clean_deadline("October 31, 2026")
    assert d == "October 31, 2026"
    assert unc is None

def test_missing_deadlines():
    d, unc = validate_and_clean_deadline(None)
    assert d is None
    assert unc is None

    d, unc = validate_and_clean_deadline("")
    assert d is None

    d, unc = validate_and_clean_deadline("N/A")
    assert d is None

def test_ambiguous_and_vague_dates_marked_uncertain():
    # "soon"
    d, unc = validate_and_clean_deadline("soon")
    assert d is None
    assert unc is not None
    assert "Ambiguous deadline" in unc

    # "next week"
    d, unc = validate_and_clean_deadline("next week")
    assert d is None
    assert unc is not None

    # "ASAP"
    d, unc = validate_and_clean_deadline("ASAP")
    assert d is None
    assert unc is not None

def test_priority_sanitization():
    # High
    t = sanitize_task({"title": "Fix bug", "priority": "HIGH"})
    assert t["priority"] == "high"

    # Medium
    t = sanitize_task({"title": "Write docs", "priority": "medium"})
    assert t["priority"] == "medium"

    # Low
    t = sanitize_task({"title": "Clean desk", "priority": "low"})
    assert t["priority"] == "low"

    # Invalid defaults to medium
    t = sanitize_task({"title": "Check logs", "priority": "urgent_critical_asap"})
    assert t["priority"] == "medium"

def test_normalize_title():
    assert normalize_title("TODO: Deploy database patch!") == "deploy database patch"
    assert normalize_title("Please make sure to review PR #12") == "review pr 12"
    assert normalize_title("Task - Submit expenses.") == "submit expenses"

def test_deduplicate_tasks():
    existing = [
        {"title": "Deploy database patch", "source_file": "notes.md"},
        {"title": "Review marketing copy", "source_file": "meeting.txt"}
    ]

    new_tasks = [
        # Duplicate of existing
        {"title": "TODO: Deploy database patch!", "source_file": "notes.md"},
        # Distinct task from same file
        {"title": "Deploy indexing script", "source_file": "notes.md"},
        # Same task name but different source file -> preserved
        {"title": "Review marketing copy", "source_file": "other_file.txt"},
        # Completely new task
        {"title": "Prepare executive summary", "source_file": "briefing.md"}
    ]

    deduped = deduplicate_tasks(new_tasks, existing)
    titles = [t["title"] for t in deduped]

    assert "TODO: Deploy database patch!" not in titles
    assert "Deploy indexing script" in titles
    assert "Review marketing copy" in titles
    assert "Prepare executive summary" in titles
    assert len(deduped) == 3

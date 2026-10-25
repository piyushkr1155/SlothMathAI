"""Tests for SQLite persistence layer."""
import pytest
from pathlib import Path
import tempfile
from storage.database import Database

@pytest.fixture
def db():
    # Use temporary file database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)
    database = Database(db_path)
    yield database
    # Cleanup
    try:
        db_path.unlink(missing_ok=True)
    except Exception:
        pass

def test_document_lifecycle(db):
    doc_id = db.save_or_update_document({
        "filename": "q4_notes.md",
        "file_path": "/path/q4_notes.md",
        "file_hash": "hash123",
        "file_type": ".md",
        "file_size": 2048,
        "status": "pending",
        "summary": "Initial summary"
    })
    assert doc_id > 0

    # Retrieve by hash
    doc = db.get_document_by_hash("hash123")
    assert doc is not None
    assert doc["filename"] == "q4_notes.md"
    assert doc["status"] == "pending"

    # Update document status and summary
    db.save_or_update_document({
        "filename": "q4_notes.md",
        "file_path": "/path/q4_notes.md",
        "file_hash": "hash123",
        "file_type": ".md",
        "file_size": 2048,
        "status": "processed",
        "summary": "Updated executive summary",
        "key_points": ["Point 1", "Point 2"]
    })

    updated = db.get_document_by_hash("hash123")
    assert updated["status"] == "processed"
    assert "Updated executive summary" in updated["summary"]

def test_task_operations(db):
    doc_id = db.save_or_update_document({
        "filename": "tasks.txt",
        "file_path": "/path/tasks.txt",
        "file_hash": "thash456",
        "file_type": ".txt",
        "file_size": 500,
        "status": "processed"
    })

    task_id = db.save_task({
        "document_id": doc_id,
        "title": "Review pull request",
        "priority": "high",
        "deadline": "2026-10-31",
        "source_file": "tasks.txt",
        "evidence": "Please review PR by Oct 31."
    })
    assert task_id > 0

    # List tasks
    pending_tasks = db.list_tasks(status="pending")
    assert len(pending_tasks) == 1
    assert pending_tasks[0]["priority"] == "high"

    # Update task status to completed
    db.update_task(task_id, {"status": "completed"})
    completed = db.list_tasks(status="completed")
    assert len(completed) == 1
    assert completed[0]["title"] == "Review pull request"

    # Update priority
    db.update_task(task_id, {"priority": "low"})
    t = db.get_task_by_id(task_id)
    assert t["priority"] == "low"

    # Delete task
    db.delete_task(task_id)
    assert db.get_task_by_id(task_id) is None

def test_briefing_persistence(db):
    b_id = db.save_briefing({
        "reference_date": "2026-10-25",
        "executive_summary": "All systems operational.",
        "top_priorities": ["Priority 1", "Priority 2"],
        "tasks_due_today": ["Task A"],
        "upcoming_deadlines": ["Task B"],
        "markdown_content": "# Briefing\nAll systems operational."
    })
    assert b_id > 0

    latest = db.get_latest_briefing()
    assert latest is not None
    assert latest["reference_date"] == "2026-10-25"
    assert len(latest["top_priorities"]) == 2
    assert "Task A" in latest["tasks_due_today"]

def test_metrics_calculation(db):
    # Add an overdue task and a completed task
    db.save_task({
        "title": "Overdue Action",
        "priority": "high",
        "deadline": "2026-10-20", # before ref date
        "status": "pending",
        "source_file": "doc1.md"
    })

    db.save_task({
        "title": "Completed Action",
        "priority": "medium",
        "deadline": "2026-10-25",
        "status": "completed",
        "source_file": "doc1.md"
    })

    db.save_or_update_document({
        "filename": "doc1.md",
        "file_path": "/path/doc1.md",
        "file_hash": "metrichash",
        "file_type": ".md",
        "file_size": 100,
        "status": "processed"
    })

    metrics = db.get_metrics(reference_date="2026-10-25")
    assert metrics["pending_tasks"] == 1
    assert metrics["completed_tasks"] == 1
    assert metrics["overdue_tasks"] == 1
    assert metrics["processed_docs"] == 1

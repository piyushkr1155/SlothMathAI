"""Tests for inbox processor, duplicate detection, and Sloth Mode workflow."""
import pytest
from pathlib import Path
import tempfile
import gc

from storage.database import Database
from services.inbox_processor import InboxProcessor

class MockAIService:
    def __init__(self):
        self.call_count = 0

    def check_status(self):
        return {
            "state": "connected",
            "is_running": True,
            "model_available": True,
            "installed_models": ["mock-model"],
            "active_model": "mock-model",
            "install_command": "",
            "message": "Mock active"
        }

    def generate_structured(self, prompt, system=None, max_retries=1):
        self.call_count += 1
        return {
            "summary": "Mock document analysis summary.",
            "key_points": ["Key decision A", "Key decision B"],
            "tasks": [
                {
                    "title": f"Action Item from run {self.call_count}",
                    "deadline": "2026-10-31",
                    "priority": "high",
                    "evidence": "Supporting sentence from text."
                }
            ],
            "important_dates": [],
            "follow_ups": ["Confirm with team"],
            "uncertainties": []
        }

@pytest.fixture
def test_env():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        root = Path(td)
        inbox = root / "inbox"
        inbox.mkdir()
        db_path = root / "test.db"
        db = Database(db_path)
        ai = MockAIService()
        proc = InboxProcessor(db=db, ai_service=ai, inbox_dir=inbox)
        yield {
            "inbox": inbox,
            "db": db,
            "ai": ai,
            "proc": proc
        }
        # Explicit garbage collection for Windows sqlite handles
        del db
        del proc
        gc.collect()

def test_sloth_mode_single_run(test_env):
    inbox = test_env["inbox"]
    proc = test_env["proc"]
    db = test_env["db"]

    # Create 2 valid text documents
    (inbox / "doc1.txt").write_text("Meeting notes for team Alpha.", encoding="utf-8")
    (inbox / "doc2.md").write_text("# Project Beta Plan\nDeliverables and deadlines.", encoding="utf-8")

    res = proc.run_sloth_mode(reference_date="2026-10-25")
    assert res["total_files"] == 2
    assert len(res["successes"]) == 2
    assert len(res["failures"]) == 0
    assert len(res["skipped"]) == 0
    assert res["new_tasks_count"] == 2

    # Verify database persistence
    docs = db.list_documents(status="processed")
    assert len(docs) == 2
    tasks = db.list_tasks(status="pending")
    assert len(tasks) == 2

def test_idempotent_sloth_mode_skips_duplicates(test_env):
    inbox = test_env["inbox"]
    proc = test_env["proc"]
    ai = test_env["ai"]

    # Write document
    doc_path = inbox / "repeat_doc.txt"
    doc_path.write_text("Constant content for repeat test.", encoding="utf-8")

    # Run 1
    res1 = proc.run_sloth_mode(reference_date="2026-10-25")
    assert len(res1["successes"]) == 1
    assert len(res1["skipped"]) == 0
    calls_after_run1 = ai.call_count

    # Run 2 (File has not changed - identical hash)
    res2 = proc.run_sloth_mode(reference_date="2026-10-25")
    assert len(res2["successes"]) == 0
    assert len(res2["skipped"]) == 1
    assert res2["skipped"][0]["filename"] == "repeat_doc.txt"
    # Local AI service should NOT have been invoked again for unchanged file
    assert ai.call_count == calls_after_run1

def test_partial_failure_resilience(test_env):
    inbox = test_env["inbox"]
    proc = test_env["proc"]
    db = test_env["db"]

    # 1 valid file, 1 empty file (failure)
    (inbox / "valid.md").write_text("# Valid Document\nActions to take.", encoding="utf-8")
    (inbox / "corrupt_empty.txt").write_text("", encoding="utf-8") # 0 bytes

    res = proc.run_sloth_mode(reference_date="2026-10-25")
    assert res["total_files"] == 2
    assert len(res["successes"]) == 1
    assert len(res["failures"]) == 1
    assert res["failures"][0]["filename"] == "corrupt_empty.txt"

    # Valid file was processed successfully despite failure of second file
    docs = db.list_documents()
    assert len(docs) == 2
    statuses = {d["filename"]: d["status"] for d in docs}
    assert statuses["valid.md"] == "processed"
    assert statuses["corrupt_empty.txt"] == "failed"

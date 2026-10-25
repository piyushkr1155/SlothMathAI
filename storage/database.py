"""Database storage layer for SlothMate AI using SQLite."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import os

class Database:
    """Encapsulates SQLite operations with WAL mode and foreign key constraints."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            from config import config
            self.db_path = config.db_path
        else:
            self.db_path = Path(db_path)
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create and configure a SQLite connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def init_db(self) -> None:
        """Create database tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL UNIQUE,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    processed_at TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    error_message TEXT,
                    summary TEXT,
                    key_points TEXT,
                    important_dates TEXT,
                    follow_ups TEXT,
                    uncertainties TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
                    deadline TEXT,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'dismissed')),
                    source_file TEXT NOT NULL,
                    evidence TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
                );
            """)

            # Briefings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS briefings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    executive_summary TEXT,
                    top_priorities TEXT,
                    tasks_due_today TEXT,
                    upcoming_deadlines TEXT,
                    decisions TEXT,
                    follow_ups TEXT,
                    can_wait TEXT,
                    uncertainties TEXT,
                    source_documents TEXT,
                    markdown_content TEXT NOT NULL
                );
            """)

            # Processing runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_at TEXT NOT NULL,
                    documents_count INTEGER NOT NULL,
                    tasks_extracted_count INTEGER NOT NULL,
                    success_count INTEGER NOT NULL,
                    failure_count INTEGER NOT NULL,
                    skipped_count INTEGER NOT NULL,
                    details TEXT
                );
            """)

            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_hash ON documents(file_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);")
            conn.commit()

    # ------------------ Document Operations ------------------

    def get_document_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document record by its SHA-256 hash."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE file_hash = ?;", (file_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?;", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_documents(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM documents WHERE status = ? ORDER BY id DESC;", (status,))
            else:
                cursor.execute("SELECT * FROM documents ORDER BY id DESC;")
            return [dict(row) for row in cursor.fetchall()]

    def save_or_update_document(self, doc: Dict[str, Any]) -> int:
        """Insert or update a document record."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            existing = self.get_document_by_hash(doc["file_hash"])
            
            def to_json(val):
                if val is None:
                    return None
                if isinstance(val, (list, dict)):
                    return json.dumps(val, ensure_ascii=False)
                return str(val)

            if existing:
                doc_id = existing["id"]
                cursor.execute("""
                    UPDATE documents SET
                        filename = ?,
                        file_path = ?,
                        file_type = ?,
                        file_size = ?,
                        processed_at = ?,
                        status = ?,
                        error_message = ?,
                        summary = ?,
                        key_points = ?,
                        important_dates = ?,
                        follow_ups = ?,
                        uncertainties = ?
                    WHERE id = ?;
                """, (
                    doc["filename"],
                    doc["file_path"],
                    doc["file_type"],
                    doc["file_size"],
                    doc.get("processed_at", now),
                    doc.get("status", "pending"),
                    doc.get("error_message"),
                    doc.get("summary"),
                    to_json(doc.get("key_points")),
                    to_json(doc.get("important_dates")),
                    to_json(doc.get("follow_ups")),
                    to_json(doc.get("uncertainties")),
                    doc_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO documents (
                        filename, file_path, file_hash, file_type, file_size,
                        processed_at, status, error_message, summary,
                        key_points, important_dates, follow_ups, uncertainties, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    doc["filename"],
                    doc["file_path"],
                    doc["file_hash"],
                    doc["file_type"],
                    doc["file_size"],
                    doc.get("processed_at"),
                    doc.get("status", "pending"),
                    doc.get("error_message"),
                    doc.get("summary"),
                    to_json(doc.get("key_points")),
                    to_json(doc.get("important_dates")),
                    to_json(doc.get("follow_ups")),
                    to_json(doc.get("uncertainties")),
                    now
                ))
                doc_id = cursor.lastrowid
            conn.commit()
            return doc_id

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document and cascade to its tasks."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?;", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ------------------ Task Operations ------------------

    def save_task(self, task: Dict[str, Any]) -> int:
        """Insert a single extracted or created task."""
        now = datetime.now(timezone.utc).isoformat()
        priority = task.get("priority", "medium").lower()
        if priority not in ("low", "medium", "high"):
            priority = "medium"
            
        status = task.get("status", "pending").lower()
        if status not in ("pending", "in_progress", "completed", "dismissed"):
            status = "pending"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    document_id, title, description, priority, deadline,
                    status, source_file, evidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                task.get("document_id"),
                task["title"].strip(),
                task.get("description"),
                priority,
                task.get("deadline"),
                status,
                task.get("source_file", "manual"),
                task.get("evidence"),
                task.get("created_at", now),
                now
            ))
            conn.commit()
            return cursor.lastrowid

    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status and status != "all":
            query += " AND status = ?"
            params.append(status)

        if priority and priority != "all":
            query += " AND priority = ?"
            params.append(priority)

        if search and search.strip():
            query += " AND (title LIKE ? OR description LIKE ? OR source_file LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term])

        # Priority ordering: high > medium > low, then deadline ascending (nulls last)
        query += """
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                    ELSE 4 
                END,
                CASE WHEN deadline IS NULL OR deadline = '' THEN 1 ELSE 0 END,
                deadline ASC,
                id DESC
            LIMIT ?;
        """
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        """Update fields of an existing task."""
        allowed_fields = {"title", "description", "priority", "deadline", "status"}
        fields_to_update = {k: v for k, v in updates.items() if k in allowed_fields}
        if not fields_to_update:
            return False

        fields_to_update["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Validate priority if present
        if "priority" in fields_to_update:
            p = fields_to_update["priority"].lower()
            fields_to_update["priority"] = p if p in ("low", "medium", "high") else "medium"

        # Validate status if present
        if "status" in fields_to_update:
            s = fields_to_update["status"].lower()
            fields_to_update["status"] = s if s in ("pending", "in_progress", "completed", "dismissed") else "pending"

        set_clause = ", ".join(f"{k} = ?" for k in fields_to_update.keys())
        values = list(fields_to_update.values()) + [task_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?;", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ------------------ Briefing Operations ------------------

    def save_briefing(self, briefing: Dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        ref_date = briefing.get("reference_date", datetime.now().strftime("%Y-%m-%d"))

        def to_json(val):
            if val is None:
                return None
            if isinstance(val, (list, dict)):
                return json.dumps(val, ensure_ascii=False)
            return str(val)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO briefings (
                    reference_date, created_at, executive_summary, top_priorities,
                    tasks_due_today, upcoming_deadlines, decisions, follow_ups,
                    can_wait, uncertainties, source_documents, markdown_content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                ref_date,
                briefing.get("created_at", now),
                briefing.get("executive_summary"),
                to_json(briefing.get("top_priorities")),
                to_json(briefing.get("tasks_due_today")),
                to_json(briefing.get("upcoming_deadlines")),
                to_json(briefing.get("decisions")),
                to_json(briefing.get("follow_ups")),
                to_json(briefing.get("can_wait")),
                to_json(briefing.get("uncertainties")),
                to_json(briefing.get("source_documents")),
                briefing.get("markdown_content", "")
            ))
            conn.commit()
            return cursor.lastrowid

    def get_latest_briefing(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM briefings ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()
            return self._parse_briefing_row(row) if row else None

    def get_briefing_by_id(self, briefing_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM briefings WHERE id = ?;", (briefing_id,))
            row = cursor.fetchone()
            return self._parse_briefing_row(row) if row else None

    def list_briefings(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM briefings ORDER BY id DESC LIMIT ?;", (limit,))
            return [self._parse_briefing_row(r) for r in cursor.fetchall()]

    def _parse_briefing_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for json_field in ("top_priorities", "tasks_due_today", "upcoming_deadlines", 
                           "decisions", "follow_ups", "can_wait", "uncertainties", "source_documents"):
            if d.get(json_field):
                try:
                    d[json_field] = json.loads(d[json_field])
                except (json.JSONDecodeError, TypeError):
                    d[json_field] = []
            else:
                d[json_field] = []
        return d

    # ------------------ Processing Runs ------------------

    def save_processing_run(self, run: Dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processing_runs (
                    run_at, documents_count, tasks_extracted_count,
                    success_count, failure_count, skipped_count, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                run.get("run_at", now),
                run.get("documents_count", 0),
                run.get("tasks_extracted_count", 0),
                run.get("success_count", 0),
                run.get("failure_count", 0),
                run.get("skipped_count", 0),
                json.dumps(run.get("details", {}), ensure_ascii=False)
            ))
            conn.commit()
            return cursor.lastrowid

    def list_processing_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM processing_runs ORDER BY id DESC LIMIT ?;", (limit,))
            runs = []
            for r in cursor.fetchall():
                rd = dict(r)
                if rd.get("details"):
                    try:
                        rd["details"] = json.loads(rd["details"])
                    except Exception:
                        pass
                runs.append(rd)
            return runs

    # ------------------ Metrics & Reporting ------------------

    def get_metrics(self, reference_date: Optional[str] = None) -> Dict[str, int]:
        """Return accurate counts from SQLite persistence."""
        if reference_date is None:
            reference_date = datetime.now().strftime("%Y-%m-%d")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tasks counts
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending';")
            pending_tasks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed';")
            completed_tasks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'in_progress';")
            in_progress_tasks = cursor.fetchone()[0]

            # Overdue tasks: pending or in_progress, with deadline strictly < reference_date
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE status IN ('pending', 'in_progress') 
                  AND deadline IS NOT NULL 
                  AND deadline != '' 
                  AND deadline < ?;
            """, (reference_date,))
            overdue_tasks = cursor.fetchone()[0]

            # Tasks due today
            cursor.execute("""
                SELECT COUNT(*) FROM tasks 
                WHERE status IN ('pending', 'in_progress') 
                  AND deadline = ?;
            """, (reference_date,))
            due_today_tasks = cursor.fetchone()[0]

            # Documents counts
            cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'processed';")
            processed_docs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'pending';")
            pending_docs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM documents WHERE status = 'failed';")
            failed_docs = cursor.fetchone()[0]

            return {
                "pending_tasks": pending_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "overdue_tasks": overdue_tasks,
                "due_today_tasks": due_today_tasks,
                "processed_docs": processed_docs,
                "pending_docs": pending_docs,
                "failed_docs": failed_docs,
                "total_docs": processed_docs + pending_docs + failed_docs,
            }

    def reset_database(self) -> None:
        """Clear all table data while preserving the schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks;")
            cursor.execute("DELETE FROM documents;")
            cursor.execute("DELETE FROM briefings;")
            cursor.execute("DELETE FROM processing_runs;")
            conn.commit()

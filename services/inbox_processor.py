"""Inbox processor and Sloth Mode workflow coordinator for SlothMate AI."""
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
import json

from config import config
from storage.database import Database
from processors.text_reader import read_text_file, compute_file_hash, TextReaderError
from processors.pdf_reader import read_pdf_file, PDFReaderError
from processors.chunking import chunk_text
from ai.local_model import LocalModelService, OllamaServiceError, ModelNotFoundError
from ai.prompts import SYSTEM_PROMPT, DOCUMENT_ANALYSIS_PROMPT
from services.task_extractor import sanitize_task, deduplicate_tasks
from services.briefing import consolidate_briefing

class InboxProcessor:
    """Orchestrates Lazy Inbox file ingestion and Sloth Mode processing."""

    def __init__(
        self,
        db: Optional[Database] = None,
        ai_service: Optional[LocalModelService] = None,
        inbox_dir: Optional[Path] = None,
        max_file_size_bytes: Optional[int] = None
    ):
        self.db = db or Database()
        self.ai_service = ai_service or LocalModelService(
            base_url=config.ollama_base_url,
            model_name=config.default_model,
            timeout=config.request_timeout_seconds,
            temperature=config.temperature
        )
        self.inbox_dir = Path(inbox_dir or config.inbox_dir)
        self.max_file_size_bytes = max_file_size_bytes or config.max_file_size_bytes
        self.supported_extensions = config.supported_extensions

    def scan_inbox(self) -> List[Path]:
        """Discover all supported candidate files in the inbox directory."""
        if not self.inbox_dir.exists():
            return []

        candidates = []
        for p in self.inbox_dir.iterdir():
            if p.is_file() and p.suffix.lower() in self.supported_extensions:
                candidates.append(p)
        return sorted(candidates, key=lambda x: x.name.lower())

    def process_single_file(
        self,
        file_path: Path,
        reference_date: Optional[str] = None,
        force_reprocess: bool = False
    ) -> Dict[str, Any]:
        """Process a single file through validation, extraction, local AI, and persistence."""
        ref_date = reference_date or datetime.now().strftime("%Y-%m-%d")
        path = Path(file_path)
        ext = path.suffix.lower()

        # 1. Basic validation
        if ext not in self.supported_extensions:
            return {
                "filename": path.name,
                "status": "failed",
                "error": f"Unsupported file extension '{ext}'. Supported: {', '.join(sorted(self.supported_extensions))}"
            }

        try:
            file_hash = compute_file_hash(path)
        except Exception as e:
            return {
                "filename": path.name,
                "status": "failed",
                "error": f"Could not read file for hashing: {str(e)}"
            }

        # 2. Duplicate detection: check if already processed
        existing = self.db.get_document_by_hash(file_hash)
        if existing and existing.get("status") == "processed" and not force_reprocess:
            return {
                "filename": path.name,
                "status": "skipped",
                "document_id": existing["id"],
                "message": "File with identical content hash has already been processed."
            }

        # 3. Read and extract content safely
        try:
            if ext in (".txt", ".md"):
                read_data = read_text_file(path, max_size_bytes=self.max_file_size_bytes)
            elif ext == ".pdf":
                read_data = read_pdf_file(path, max_size_bytes=self.max_file_size_bytes)
            else:
                raise ValueError(f"Unsupported extension: {ext}")
        except (TextReaderError, PDFReaderError, Exception) as e:
            doc_id = self.db.save_or_update_document({
                "filename": path.name,
                "file_path": str(path.resolve()),
                "file_hash": file_hash,
                "file_type": ext,
                "file_size": path.stat().st_size if path.exists() else 0,
                "status": "failed",
                "error_message": str(e)
            })
            return {
                "filename": path.name,
                "status": "failed",
                "document_id": doc_id,
                "error": str(e)
            }

        # 4. Chunk text if necessary
        chunks = chunk_text(read_data["text"], chunk_size=config.chunk_size_chars, overlap=config.chunk_overlap_chars)
        
        # 5. Send to Local AI Model
        combined_analysis = {
            "summary": "",
            "key_points": [],
            "tasks": [],
            "important_dates": [],
            "follow_ups": [],
            "uncertainties": []
        }

        try:
            for chunk in chunks:
                prompt = DOCUMENT_ANALYSIS_PROMPT.format(
                    filename=path.name,
                    reference_date=ref_date,
                    document_text=chunk.text
                )
                chunk_result = self.ai_service.generate_structured(
                    prompt=prompt,
                    system=SYSTEM_PROMPT
                )

                # Merge chunk results
                if chunk_result.get("summary"):
                    if combined_analysis["summary"]:
                        combined_analysis["summary"] += " " + chunk_result["summary"]
                    else:
                        combined_analysis["summary"] = chunk_result["summary"]

                for list_key in ("key_points", "tasks", "important_dates", "follow_ups", "uncertainties"):
                    items = chunk_result.get(list_key, [])
                    if isinstance(items, list):
                        combined_analysis[list_key].extend(items)

        except (OllamaServiceError, ModelNotFoundError, Exception) as ai_err:
            doc_id = self.db.save_or_update_document({
                "filename": path.name,
                "file_path": str(path.resolve()),
                "file_hash": file_hash,
                "file_type": ext,
                "file_size": read_data["file_size"],
                "status": "failed",
                "error_message": f"AI Processing Error: {str(ai_err)}"
            })
            return {
                "filename": path.name,
                "status": "failed",
                "document_id": doc_id,
                "error": str(ai_err)
            }

        # 6. Sanitize and validate tasks
        sanitized_tasks = []
        for raw_task in combined_analysis.get("tasks", []):
            if isinstance(raw_task, dict):
                st = sanitize_task(raw_task, default_source=path.name)
                sanitized_tasks.append(st)
                if st.get("uncertainty_note"):
                    combined_analysis["uncertainties"].append(st["uncertainty_note"])

        # Deduplicate within document
        existing_doc_tasks = self.db.list_tasks()
        unique_tasks = deduplicate_tasks(sanitized_tasks, existing_doc_tasks)

        # 7. Persist Document in SQLite
        doc_id = self.db.save_or_update_document({
            "filename": path.name,
            "file_path": str(path.resolve()),
            "file_hash": file_hash,
            "file_type": ext,
            "file_size": read_data["file_size"],
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "status": "processed",
            "error_message": None,
            "summary": combined_analysis.get("summary", ""),
            "key_points": combined_analysis.get("key_points", []),
            "important_dates": combined_analysis.get("important_dates", []),
            "follow_ups": combined_analysis.get("follow_ups", []),
            "uncertainties": combined_analysis.get("uncertainties", [])
        })

        # 8. Persist Tasks in SQLite
        saved_task_ids = []
        for task in unique_tasks:
            task["document_id"] = doc_id
            t_id = self.db.save_task(task)
            saved_task_ids.append(t_id)

        return {
            "filename": path.name,
            "status": "processed",
            "document_id": doc_id,
            "tasks_count": len(saved_task_ids),
            "summary": combined_analysis.get("summary", "")
        }

    def run_sloth_mode(
        self,
        reference_date: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """Execute Sloth Mode: batch process eligible inbox files and generate a briefing."""
        ref_date = reference_date or datetime.now().strftime("%Y-%m-%d")
        candidate_files = self.scan_inbox()
        total_files = len(candidate_files)

        successes = []
        failures = []
        skipped = []
        newly_extracted_tasks_count = 0

        for idx, file_path in enumerate(candidate_files, 1):
            if progress_callback:
                progress_callback(idx, total_files, file_path.name, "Processing document with local AI...")

            res = self.process_single_file(file_path, reference_date=ref_date)
            status = res.get("status")

            if status == "processed":
                successes.append(res)
                newly_extracted_tasks_count += res.get("tasks_count", 0)
            elif status == "skipped":
                skipped.append(res)
            else:
                failures.append(res)

        # Generate a consolidated briefing across all active processed documents & pending tasks
        active_docs = self.db.list_documents(status="processed")
        active_tasks = self.db.list_tasks(status="pending")
        
        briefing_dict = consolidate_briefing(
            documents=active_docs,
            tasks=active_tasks,
            reference_date=ref_date,
            ai_service=self.ai_service
        )

        briefing_id = self.db.save_briefing(briefing_dict)
        briefing_dict["id"] = briefing_id

        # Record processing run report
        run_dict = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "documents_count": total_files,
            "tasks_extracted_count": newly_extracted_tasks_count,
            "success_count": len(successes),
            "failure_count": len(failures),
            "skipped_count": len(skipped),
            "details": {
                "successes": [s["filename"] for s in successes],
                "failures": [{f["filename"]: f.get("error")} for f in failures],
                "skipped": [sk["filename"] for sk in skipped],
                "briefing_id": briefing_id
            }
        }
        self.db.save_processing_run(run_dict)

        return {
            "total_files": total_files,
            "successes": successes,
            "failures": failures,
            "skipped": skipped,
            "new_tasks_count": newly_extracted_tasks_count,
            "briefing": briefing_dict
        }

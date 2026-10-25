"""Task extraction, normalization, and deduplication for SlothMate AI."""
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Regex patterns for explicit dates
EXPLICIT_DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",                  # 2026-10-31
    r"\b\d{2}/\d{2}/\d{4}\b",                  # 31/10/2026 or 10/31/2026
    r"\b\d{4}/\d{2}/\d{2}\b",                  # 2026/10/31
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",  # October 31, 2026
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}\b",  # 31 October 2026
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b",            # Oct 31
]

# Ambiguous, relative, or subjective time expressions
VAGUE_TIMING_PATTERNS = [
    r"\bsoon\b", r"\basap\b", r"\blater\b", r"\bnext week\b",
    r"\bsometime\b", r"\btomorrow\b", r"\bin a few days\b",
    r"\bnext month\b", r"\bupcoming\b", r"\beventually\b",
    r"\bwhen possible\b", r"\bat earliest\b", r"\btbd\b"
]

def normalize_title(title: str) -> str:
    """Normalize task title for duplicate comparison."""
    t = title.lower().strip()
    # Remove leading common bullet points or action markers repeatedly
    prefix_pattern = r"^(?:(?:todo|action item|task|please|make sure to|ensure)\s*[:\-]?\s*)+"
    t = re.sub(prefix_pattern, "", t, flags=re.IGNORECASE)
    # Remove punctuation
    t = re.sub(r"[^\w\s]", "", t)
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def validate_and_clean_deadline(deadline: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Validate a deadline string.
    
    Returns:
        (clean_deadline, uncertainty_note)
        If the deadline is explicit, returns (clean_deadline, None).
        If ambiguous or relative, returns (None, note explaining why it was marked uncertain).
    """
    if not deadline or not str(deadline).strip():
        return (None, None)

    d_str = str(deadline).strip()
    if d_str.lower() in ("null", "none", "n/a", "undefined", "tbd"):
        return (None, None)

    # Check for vague timing
    for v_pat in VAGUE_TIMING_PATTERNS:
        if re.search(v_pat, d_str, re.IGNORECASE):
            return (None, f"Ambiguous deadline '{d_str}' was marked as uncertain rather than assigned as a firm date.")

    # Check for explicit date match
    is_explicit = any(re.search(pat, d_str, re.IGNORECASE) for pat in EXPLICIT_DATE_PATTERNS)
    if is_explicit:
        # Try normalizing ISO date format if possible
        iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", d_str)
        if iso_match:
            return (iso_match.group(1), None)
        return (d_str, None)

    # If it is neither clearly explicit nor standard, mark as uncertain
    return (None, f"Unverified date expression '{d_str}' recorded as uncertain information.")

def sanitize_task(task_raw: Dict[str, Any], default_source: str = "unknown") -> Dict[str, Any]:
    """Validate and sanitize fields of an extracted task."""
    title = str(task_raw.get("title", "")).strip()
    if not title:
        title = "Untitled Action Item"

    priority = str(task_raw.get("priority", "medium")).lower().strip()
    if priority not in ("low", "medium", "high"):
        priority = "medium"

    deadline_raw = task_raw.get("deadline")
    clean_deadline, uncertainty = validate_and_clean_deadline(deadline_raw)

    source_file = str(task_raw.get("source_file") or default_source).strip()
    evidence = str(task_raw.get("evidence", "")).strip()

    return {
        "title": title,
        "description": task_raw.get("description", ""),
        "priority": priority,
        "deadline": clean_deadline,
        "source_file": source_file,
        "evidence": evidence,
        "uncertainty_note": uncertainty
    }

def deduplicate_tasks(
    new_tasks: List[Dict[str, Any]],
    existing_tasks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Filter out duplicate tasks while preserving distinct items.
    
    Duplicates are identified by comparing normalized titles and source files.
    """
    seen_normalized = set()
    for et in existing_tasks:
        norm = (normalize_title(et.get("title", "")), et.get("source_file", "").lower())
        if norm[0]:
            seen_normalized.add(norm)

    unique_new = []
    for nt in new_tasks:
        norm = (normalize_title(nt.get("title", "")), nt.get("source_file", "").lower())
        if not norm[0]:
            continue
        if norm not in seen_normalized:
            seen_normalized.add(norm)
            unique_new.append(nt)

    return unique_new

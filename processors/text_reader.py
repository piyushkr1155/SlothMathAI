"""Text and Markdown document processor for SlothMate AI."""
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple
import re

class TextReaderError(Exception):
    """Raised when reading or validating a text/markdown file fails."""
    pass

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for duplicate detection."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()

def compute_bytes_hash(content_bytes: bytes) -> str:
    """Compute SHA-256 hash from raw bytes."""
    return hashlib.sha256(content_bytes).hexdigest()

def read_text_file(file_path: Path, max_size_bytes: int = 20 * 1024 * 1024) -> Dict[str, Any]:
    """Read a .txt or .md file with encoding detection and security validation.
    
    Returns:
        dict: {
            "text": str,
            "filename": str,
            "file_type": str,
            "file_size": int,
            "file_hash": str,
            "char_count": int,
            "word_count": int
        }
    """
    path = Path(file_path)
    if not path.exists():
        raise TextReaderError(f"File not found: {path.name}")
    
    size = path.stat().st_size
    if size == 0:
        raise TextReaderError(f"File is empty: {path.name}")
    
    if size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise TextReaderError(f"File exceeds maximum allowed size of {max_mb:.0f} MB ({path.name}: {size / (1024*1024):.2f} MB)")

    raw_bytes = path.read_bytes()
    file_hash = compute_bytes_hash(raw_bytes)

    # Attempt decodings in order of likelihood
    text = None
    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "utf-16"]
    for enc in encodings:
        try:
            text = raw_bytes.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        raise TextReaderError(f"Unable to decode text file with standard encodings: {path.name}")

    # Sanitize NULL bytes and normalize newlines
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if not text.strip():
        raise TextReaderError(f"File contains only whitespace or control characters: {path.name}")

    return {
        "text": text,
        "filename": path.name,
        "file_type": path.suffix.lower(),
        "file_size": size,
        "file_hash": file_hash,
        "char_count": len(text),
        "word_count": len(text.split()),
    }

"""PDF document processor for SlothMate AI using PyMuPDF."""
from pathlib import Path
from typing import Dict, Any, List
import pymupdf
from processors.text_reader import compute_bytes_hash

class PDFReaderError(Exception):
    """Raised when reading or extracting text from a PDF fails."""
    pass

def read_pdf_file(file_path: Path, max_size_bytes: int = 20 * 1024 * 1024) -> Dict[str, Any]:
    """Extract text from a PDF document with security checks and page awareness.
    
    Returns:
        dict: {
            "text": str,
            "filename": str,
            "file_type": ".pdf",
            "file_size": int,
            "file_hash": str,
            "page_count": int,
            "char_count": int,
            "word_count": int
        }
    """
    path = Path(file_path)
    if not path.exists():
        raise PDFReaderError(f"PDF file not found: {path.name}")
    
    size = path.stat().st_size
    if size == 0:
        raise PDFReaderError(f"PDF file is empty (0 bytes): {path.name}")
        
    if size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise PDFReaderError(f"PDF exceeds maximum allowed size of {max_mb:.0f} MB ({path.name}: {size / (1024*1024):.2f} MB)")

    raw_bytes = path.read_bytes()
    file_hash = compute_bytes_hash(raw_bytes)

    try:
        doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
    except Exception as e:
        raise PDFReaderError(f"Corrupt or invalid PDF file ({path.name}): {str(e)}")

    with doc:
        if doc.is_encrypted:
            raise PDFReaderError(f"PDF is password-protected or encrypted: {path.name}")

        page_count = len(doc)
        if page_count == 0:
            raise PDFReaderError(f"PDF has no pages: {path.name}")

        pages_text: List[str] = []
        for i, page in enumerate(doc):
            try:
                page_text = page.get_text("text")
                if page_text and page_text.strip():
                    # Clean NULL characters and normalize
                    cleaned = page_text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
                    pages_text.append(f"--- [Page {i + 1}] ---\n{cleaned}")
            except Exception as pe:
                pages_text.append(f"--- [Page {i + 1}] (Extraction Error: {str(pe)}) ---")

        full_text = "\n\n".join(pages_text).strip()

        if not full_text or len(full_text.replace("-", "").strip()) == 0:
            raise PDFReaderError(
                f"No extractable text found in '{path.name}'. The PDF may contain scanned images only without an embedded text layer."
            )

        return {
            "text": full_text,
            "filename": path.name,
            "file_type": ".pdf",
            "file_size": size,
            "file_hash": file_hash,
            "page_count": page_count,
            "char_count": len(full_text),
            "word_count": len(full_text.split()),
        }

"""Tests for text, markdown, and PDF document processors."""
import pytest
from pathlib import Path
import tempfile
import pymupdf

from processors.text_reader import read_text_file, compute_file_hash, TextReaderError
from processors.pdf_reader import read_pdf_file, PDFReaderError
from processors.chunking import chunk_text

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)

def test_read_valid_text_file(temp_dir):
    p = temp_dir / "notes.txt"
    p.write_text("Meeting summary with important points.", encoding="utf-8")
    
    res = read_text_file(p)
    assert res["filename"] == "notes.txt"
    assert res["file_type"] == ".txt"
    assert "Meeting summary" in res["text"]
    assert res["word_count"] == 5
    assert len(res["file_hash"]) == 64

def test_read_valid_markdown_file(temp_dir):
    p = temp_dir / "agenda.md"
    p.write_text("# Agenda\n- [ ] Task 1\n- [ ] Task 2", encoding="utf-8")
    
    res = read_text_file(p)
    assert res["filename"] == "agenda.md"
    assert res["file_type"] == ".md"
    assert "# Agenda" in res["text"]

def test_empty_text_file_rejected(temp_dir):
    p = temp_dir / "empty.txt"
    p.write_text("", encoding="utf-8")
    
    with pytest.raises(TextReaderError, match="empty"):
        read_text_file(p)

def test_whitespace_only_file_rejected(temp_dir):
    p = temp_dir / "spaces.txt"
    p.write_text("   \n\n\t  ", encoding="utf-8")
    
    with pytest.raises(TextReaderError, match="whitespace"):
        read_text_file(p)

def test_oversized_file_rejected(temp_dir):
    p = temp_dir / "huge.txt"
    p.write_text("a" * 1024, encoding="utf-8")
    
    with pytest.raises(TextReaderError, match="exceeds maximum allowed size"):
        read_text_file(p, max_size_bytes=500)

def test_pdf_extraction_valid(temp_dir):
    pdf_path = temp_dir / "test.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "SlothMate AI PDF Report. Action item: submit review.")
    doc.save(str(pdf_path))
    doc.close()

    res = read_pdf_file(pdf_path)
    assert res["filename"] == "test.pdf"
    assert res["file_type"] == ".pdf"
    assert res["page_count"] == 1
    assert "SlothMate AI PDF Report" in res["text"]

def test_empty_pdf_rejected(temp_dir):
    pdf_path = temp_dir / "empty.pdf"
    doc = pymupdf.open()
    doc.new_page()  # blank page without text
    doc.save(str(pdf_path))
    doc.close()

    with pytest.raises(PDFReaderError, match="No extractable text found"):
        read_pdf_file(pdf_path)

def test_chunking_small_text():
    text = "Short document content."
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].total_chunks == 1
    assert chunks[0].text == text

def test_chunking_large_text():
    paragraphs = [f"Paragraph {i}: " + ("content details " * 20) for i in range(10)]
    full_text = "\n\n".join(paragraphs)
    
    chunks = chunk_text(full_text, chunk_size=600, overlap=100)
    assert len(chunks) > 1
    assert all(c.total_chunks == len(chunks) for c in chunks)
    for i, c in enumerate(chunks):
        assert c.chunk_index == i

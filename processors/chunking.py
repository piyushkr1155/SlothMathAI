"""Text chunking utility for large documents in SlothMate AI."""
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class TextChunk:
    chunk_index: int
    total_chunks: int
    text: str
    char_start: int
    char_end: int

def chunk_text(
    text: str,
    chunk_size: int = 3500,
    overlap: int = 350
) -> List[TextChunk]:
    """Split text into manageable chunks preserving paragraph/sentence boundaries.
    
    If text length is <= chunk_size, returns a single chunk.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    total_len = len(clean_text)
    if total_len <= chunk_size:
        return [TextChunk(
            chunk_index=0,
            total_chunks=1,
            text=clean_text,
            char_start=0,
            char_end=total_len
        )]

    chunks_data = []
    start = 0

    while start < total_len:
        end = min(start + chunk_size, total_len)

        # If not at the end of the text, look for a clean break (paragraph or sentence)
        if end < total_len:
            # Try to break at a double newline (paragraph boundary)
            para_break = clean_text.rfind("\n\n", start + overlap, end)
            if para_break != -1:
                end = para_break + 2
            else:
                # Try single newline
                line_break = clean_text.rfind("\n", start + overlap, end)
                if line_break != -1:
                    end = line_break + 1
                else:
                    # Try sentence boundary (. followed by space)
                    sent_break = clean_text.rfind(". ", start + overlap, end)
                    if sent_break != -1:
                        end = sent_break + 2
                    else:
                        # Try space
                        space_break = clean_text.rfind(" ", start + overlap, end)
                        if space_break != -1:
                            end = space_break + 1

        chunk_str = clean_text[start:end].strip()
        if chunk_str:
            chunks_data.append((chunk_str, start, end))

        # Advance start point considering overlap
        if end >= total_len:
            break
        start = max(end - overlap, start + 1)

    total_chunks = len(chunks_data)
    return [
        TextChunk(
            chunk_index=i,
            total_chunks=total_chunks,
            text=c[0],
            char_start=c[1],
            char_end=c[2]
        )
        for i, c in enumerate(chunks_data)
    ]

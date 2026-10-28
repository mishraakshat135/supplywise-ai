"""Split long documents into overlapping chunks (paragraph-aware).

TODO(INTEGRATION: RAG): tune CHUNK_SIZE / OVERLAP after testing retrieval quality on the
real contracts/policies (smaller chunks = more precise, larger = more context).
"""
from __future__ import annotations

import re

CHUNK_SIZE = 800   # characters
OVERLAP = 120


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        while len(para) > chunk_size:  # very long paragraph: hard split
            head, para = para[:chunk_size], para[chunk_size - overlap:]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            tail = current[-overlap:] if current else ""
            current = f"{tail}\n\n{para}".strip() if tail else para
    if current:
        chunks.append(current)
    return chunks

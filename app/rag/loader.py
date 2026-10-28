"""Text extraction from uploaded files (.txt, .md, .csv, .pdf).

TODO(INTEGRATION: RAG): add .docx support (python-docx) or OCR for scanned PDFs if needed.
"""
from __future__ import annotations

import io

from app.core.exceptions import BusinessRuleError


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith((".txt", ".md", ".csv")):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader  # pip install pypdf
        except ImportError as exc:
            raise BusinessRuleError("PDF support needs `pip install pypdf`.") from exc
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    raise BusinessRuleError("Unsupported file type. Upload .txt, .md, .csv or .pdf.")

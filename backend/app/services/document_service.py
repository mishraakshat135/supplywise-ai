"""Document metadata in PostgreSQL; vectors in ChromaDB through the AI module's own classes.

Uses only public AI classes: DocumentProcessor.split_documents, EmbeddingModel, RAGRetriever.add_documents.
Known issue in ai/rag/document_processor.py (NOT edited, reported to the AI owner): load_document() has
`PyPDFLoader(str(path).load())` so PDFs fail there. We therefore load PDFs with PyPDFLoader ourselves and
only use the AI splitter. .txt goes through the normal path.
"""
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import REPO_ROOT, settings
from ..core.actors import Actor
from ..core.exceptions import AIUnavailableError, BusinessRuleError, NotFoundError
from ..models import Document
from . import ai_service

log = logging.getLogger("supplywise.documents")
ALLOWED = {".pdf": {"application/pdf"}, ".txt": {"text/plain"}}
KB_DIR = REPO_ROOT / "ai" / "knowledge_base" / "raw_documents"


class PolicyIndexer:
    def __init__(self):
        ai_service._ensure_repo_on_path()
        try:
            from ai.rag.document_processor import DocumentProcessor
            from ai.rag.embeddings import EmbeddingModel
            from ai.rag.retriever import RAGRetriever
        except ImportError as exc:
            raise AIUnavailableError(f"RAG dependencies are missing ({exc}). Run: pip install -r requirements-ai.txt")
        self._processor = DocumentProcessor()
        self._retriever = RAGRetriever(EmbeddingModel(), settings.chroma_dir, settings.POLICY_COLLECTION)

    def index_file(self, path: Path, source_name: str) -> int:
        if path.suffix.lower() == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader
            docs = PyPDFLoader(str(path)).load()
            chunks = self._processor.split_documents(docs)
        else:
            chunks = self._processor.process_file(path)
        for c in chunks:
            c.metadata["source"] = source_name  # unique per upload, so delete-by-source is safe
        return self._retriever.add_documents(chunks)

    def delete_source(self, source_name: str) -> None:
        import chromadb
        client = chromadb.PersistentClient(path=str(Path(settings.chroma_dir).resolve()))
        client.get_or_create_collection(settings.POLICY_COLLECTION).delete(where={"source": source_name})


_indexer: Optional[PolicyIndexer] = None


def get_indexer():
    global _indexer
    if _indexer is None:
        _indexer = PolicyIndexer()
    return _indexer


def set_indexer(indexer) -> None:  # tests
    global _indexer
    _indexer = indexer


def _safe_name(filename: str) -> str:
    base = os.path.basename(filename.replace("\\", "/"))
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)[:100] or "document"


def _validate(filename: str, content_type: Optional[str], raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise BusinessRuleError("Only PDF and TXT files are supported")
    if content_type and content_type.split(";")[0] not in ALLOWED[ext] | {"application/octet-stream"}:
        raise BusinessRuleError(f"Content type {content_type} does not match a {ext} file")
    if not raw:
        raise BusinessRuleError("The file is empty")
    if len(raw) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise BusinessRuleError(f"File is larger than {settings.MAX_UPLOAD_MB} MB")
    if ext == ".pdf" and not raw.startswith(b"%PDF"):
        raise BusinessRuleError("File does not look like a valid PDF")
    if ext == ".txt":
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            raise BusinessRuleError("Text files must be UTF-8 encoded")
    return ext


def to_dict(d: Document) -> dict:
    return {"id": d.id, "filename": d.filename, "content_type": d.content_type, "size_bytes": d.size_bytes,
            "status": d.status, "n_chunks": d.n_chunks, "error": d.error, "uploaded_at": d.uploaded_at.isoformat(),
            "source": "upload", "readonly": False}


def upload(db: Session, filename: str, content_type: Optional[str], raw: bytes, actor: Actor) -> dict:
    _validate(filename, content_type, raw)
    stored = f"{uuid.uuid4().hex[:8]}_{_safe_name(filename)}"
    directory = settings.upload_path
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / stored
    path.write_bytes(raw)
    doc = Document(filename=_safe_name(filename), stored_name=stored, content_type=content_type, size_bytes=len(raw),
                   uploaded_by=actor.id)
    db.add(doc)
    db.commit()
    try:
        doc.n_chunks = get_indexer().index_file(path, stored)
        doc.status = "indexed"
    except Exception as exc:  # keep the file + record so the user can see what failed
        log.exception("Indexing failed for %s", stored)
        doc.status, doc.error = "failed", f"{type(exc).__name__}: {exc}"[:300]
    db.commit()
    return to_dict(doc)


def list_documents(db: Session) -> list[dict]:
    uploaded = [to_dict(d) for d in db.scalars(select(Document).order_by(Document.id.desc()))]
    repo = []
    if KB_DIR.is_dir():  # the AI module's own knowledge base, shown read-only
        for p in sorted(KB_DIR.iterdir()):
            if p.is_file() and p.suffix.lower() in ALLOWED:
                repo.append({"id": None, "filename": p.name, "content_type": None, "size_bytes": p.stat().st_size,
                             "status": "indexed", "n_chunks": None, "error": None, "uploaded_at": None,
                             "source": "repository", "readonly": True})
    return uploaded + repo


def get(db: Session, doc_id: int) -> dict:
    d = db.get(Document, doc_id)
    if not d:
        raise NotFoundError(f"Document {doc_id} not found")
    return to_dict(d)


def delete(db: Session, doc_id: int) -> dict:
    d = db.get(Document, doc_id)
    if not d:
        raise NotFoundError(f"Document {doc_id} not found")
    vectors_removed = True
    try:
        if d.status == "indexed":
            get_indexer().delete_source(d.stored_name)
    except Exception:
        log.exception("Could not remove vectors for %s", d.stored_name)
        vectors_removed = False
    (settings.upload_path / d.stored_name).unlink(missing_ok=True)
    db.delete(d)
    db.commit()
    return {"deleted": True, "vectors_removed": vectors_removed}

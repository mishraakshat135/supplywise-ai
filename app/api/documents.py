"""Document Management + AI Assistant (RAG).
TODO(INTEGRATION: FRONTEND): Document Management screen (upload/list/delete) and AI Assistant chat box.
TODO(INTEGRATION: RAG): the RAG member owns app/rag/*. Uploading a document only INDEXES it
(chunk + embed) - the LLM is never retrained."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.database import get_db
from app.models.entities import Document
from app.rag.factory import get_llm, get_retriever
from app.rag.llm import LLMError
from app.rag.loader import extract_text
from app.schemas.schemas import AskRequest, AskResponse, DocumentOut

router = APIRouter(tags=["documents & assistant"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile = File(...), doc_type: str = Form("policy"),
                          db: Session = Depends(get_db)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise BusinessRuleError("File too large (max 10 MB).")
    filename = Path(file.filename or "document.txt").name  # strip any path parts
    text = extract_text(filename, data)
    if not text.strip():
        raise BusinessRuleError("No readable text found in the document.")

    doc = Document(filename=filename, doc_type=doc_type, content=text)
    db.add(doc)
    db.flush()
    doc.num_chunks = get_retriever().index_document(doc.id, filename, text)
    db.commit()
    db.refresh(doc)
    # Optional: keep the original file on disk too.
    upload_dir = Path(get_settings().upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / f"{doc.id}_{filename}").write_bytes(data)
    return doc


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise NotFoundError(f"Document {doc_id} not found.")
    get_retriever().remove_document(doc_id)
    db.delete(doc)
    db.commit()


ASSISTANT_SYSTEM = ("You answer questions about supplier contracts and purchasing policies using ONLY "
                    "the EVIDENCE passages. Cite sources as [source: filename]. If the evidence does not "
                    "contain the answer, say so. Never invent numbers or terms.")


@router.post("/assistant/ask", response_model=AskResponse)
def ask(body: AskRequest):
    """Natural-language question -> retrieve passages -> LLM answer with citations.
    TODO(INTEGRATION: LLM): add tool calling so the assistant can also look up live stock,
    forecasts and purchase orders (call the service functions in app/services/*), instead of
    only answering from documents."""
    chunks = get_retriever().search(body.question, k=body.top_k)
    if not chunks:
        return AskResponse(answer="I couldn't find anything relevant in the uploaded documents.", sources=[])
    evidence = "\n\n".join(f"[source: {c.filename}] {c.text}" for c in chunks)
    fallback = "Most relevant passages found:\n\n" + "\n\n".join(
        f"- ({c.filename}) {c.text[:300]}" for c in chunks)
    try:
        answer = get_llm().complete(ASSISTANT_SYSTEM, f"QUESTION: {body.question}\n\nEVIDENCE:\n{evidence}",
                                    fallback=fallback)
    except LLMError:
        answer = fallback
    return AskResponse(answer=answer, sources=[c.to_dict() for c in chunks])

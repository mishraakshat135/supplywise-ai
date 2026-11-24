from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ...core.actors import Actor
from ...database.session import get_db
from ...schemas.requests import ChatRequest
from ...services import assistant_service, document_service as svc
from ..dependencies import get_actor

router = APIRouter(prefix="/api", tags=["assistant-documents"])


@router.post("/assistant/chat")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    return assistant_service.chat(db, body.question)


@router.post("/documents/upload", status_code=201)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    raw = await file.read()
    return svc.upload(db, file.filename or "document", file.content_type, raw, actor)


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return svc.list_documents(db)


@router.get("/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    return svc.get(db, doc_id)


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), _: Actor = Depends(get_actor)):
    return svc.delete(db, doc_id)

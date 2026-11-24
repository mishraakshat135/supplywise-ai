from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.actors import Actor
from ...database.session import get_db
from ...schemas.requests import DecisionNote, RecommendationGenerate
from ...services import procurement_service as svc
from ..dependencies import get_actor

router = APIRouter(prefix="/api/procurement", tags=["procurement"])


@router.post("/recommendations", status_code=201)
def generate_recommendations(body: RecommendationGenerate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    """Runs forecast -> reorder calculation -> existing multi-agent workflow. Nothing is ordered."""
    if body.product_id:
        return svc.generate(db, body.product_id, actor, body.force)
    return svc.generate_all(db, actor, body.force)


@router.get("/recommendations")
def list_recommendations(status: Optional[str] = None, limit: int = Query(100, ge=1, le=500),
                         offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return svc.list_recs(db, status, limit, offset)


@router.get("/recommendations/{rec_id}")
def get_recommendation(rec_id: int, db: Session = Depends(get_db)):
    return svc.rec_to_dict(db, svc.get_rec(db, rec_id))


@router.post("/recommendations/{rec_id}/approve")
def approve(rec_id: int, body: DecisionNote = DecisionNote(), db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.approve(db, rec_id, actor, body.note)


@router.post("/recommendations/{rec_id}/reject")
def reject(rec_id: int, body: DecisionNote = DecisionNote(), db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.reject(db, rec_id, actor, body.note)


@router.post("/recommendations/{rec_id}/flag")
def flag(rec_id: int, body: DecisionNote = DecisionNote(), db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.flag(db, rec_id, actor, body.note)

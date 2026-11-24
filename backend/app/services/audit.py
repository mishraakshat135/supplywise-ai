from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.actors import Actor
from ..models import ApprovalHistory


def log_action(db: Session, entity_type: str, entity_id: int, action: str, actor: Actor,
               from_status=None, to_status=None, comment=None) -> None:
    db.add(ApprovalHistory(entity_type=entity_type, entity_id=entity_id, action=action, from_status=from_status,
                           to_status=to_status, actor_id=actor.id, actor_label=actor.label, comment=comment))


def history(db: Session, entity_type: str, entity_id: int) -> list[ApprovalHistory]:
    return list(db.scalars(select(ApprovalHistory).where(ApprovalHistory.entity_type == entity_type,
                                                         ApprovalHistory.entity_id == entity_id)
                           .order_by(ApprovalHistory.id)))

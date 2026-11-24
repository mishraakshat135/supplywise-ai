from fastapi import Depends, Header
from sqlalchemy.orm import Session

from ..config import settings
from ..core.actors import SYSTEM_ACTOR, Actor
from ..core.exceptions import PermissionDeniedError, UnauthorizedError
from ..core.security import decode_token
from ..database.session import get_db
from ..models import User


def get_actor(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Actor:
    """AUTH_ENABLED=false -> everyone is the system admin (the frontend has no login yet)."""
    if not settings.AUTH_ENABLED:
        return SYSTEM_ACTOR
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    claims = decode_token(authorization.split(" ", 1)[1])
    user = db.get(User, int(claims["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or disabled")
    return Actor(user.id, user.full_name or user.email, user.role)


def require_manager(actor: Actor = Depends(get_actor)) -> Actor:
    if not actor.is_manager:
        raise PermissionDeniedError("This action requires a manager or admin")
    return actor


def require_admin(actor: Actor = Depends(get_actor)) -> Actor:
    if actor.role != "admin":
        raise PermissionDeniedError("This action requires an admin")
    return actor

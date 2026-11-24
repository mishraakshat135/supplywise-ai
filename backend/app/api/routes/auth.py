from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...config import settings
from ...core.exceptions import BusinessRuleError, ConflictError, UnauthorizedError
from ...core.security import create_access_token, hash_password, verify_password
from ...database.session import get_db
from ...models import User
from ...schemas.requests import LoginRequest, UserCreate
from ..dependencies import get_actor, require_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def auth_status():
    return {"auth_enabled": settings.AUTH_ENABLED}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    if not settings.AUTH_ENABLED:
        raise BusinessRuleError("Authentication is disabled (AUTH_ENABLED=false)")
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password")
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "role": user.role,
            "name": user.full_name}


@router.get("/me")
def me(actor=Depends(get_actor)):
    return {"id": actor.id, "name": actor.label, "role": actor.role}


@router.post("/users", status_code=201, dependencies=[Depends(require_admin)])
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.email) == body.email.lower())):
        raise ConflictError("A user with this email already exists")
    u = User(email=body.email, full_name=body.full_name, password_hash=hash_password(body.password), role=body.role)
    db.add(u)
    db.commit()
    return {"id": u.id, "email": u.email, "role": u.role}

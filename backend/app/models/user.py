from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.session import Base
from .base_mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="buyer")  # admin | manager | buyer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

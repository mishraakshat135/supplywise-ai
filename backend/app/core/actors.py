from dataclasses import dataclass
from typing import Optional

MANAGER_ROLES = ("manager", "admin")


@dataclass(frozen=True)
class Actor:
    id: Optional[int]
    label: str
    role: str

    @property
    def is_manager(self) -> bool:
        return self.role in MANAGER_ROLES


SYSTEM_ACTOR = Actor(None, "system", "admin")  # used when AUTH_ENABLED=false

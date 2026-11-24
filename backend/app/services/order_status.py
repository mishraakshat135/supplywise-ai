"""Purchase-order lifecycle. Invalid jumps (e.g. Received -> Draft) are impossible by construction."""
from enum import Enum

from ..core.exceptions import ConflictError, BusinessRuleError


class POStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ORDERED = "ordered"  # recorded internally only; the system never contacts suppliers
    RECEIVED = "received"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# Labels match what the existing frontend renders.
LABELS = {POStatus.DRAFT: "Draft", POStatus.PENDING_APPROVAL: "Pending Approval", POStatus.APPROVED: "Approved",
          POStatus.ORDERED: "Ordered", POStatus.RECEIVED: "Received", POStatus.REJECTED: "Rejected",
          POStatus.CANCELLED: "Cancelled"}

TRANSITIONS = {
    POStatus.DRAFT: {POStatus.PENDING_APPROVAL, POStatus.CANCELLED},
    POStatus.PENDING_APPROVAL: {POStatus.APPROVED, POStatus.REJECTED, POStatus.CANCELLED},
    POStatus.APPROVED: {POStatus.ORDERED, POStatus.CANCELLED},
    POStatus.ORDERED: {POStatus.RECEIVED, POStatus.CANCELLED},
    POStatus.RECEIVED: set(), POStatus.REJECTED: set(), POStatus.CANCELLED: set(),
}


def parse_status(value: str) -> POStatus:
    v = value.strip().lower().replace(" ", "_")
    try:
        return POStatus(v)
    except ValueError:
        raise BusinessRuleError(f"Unknown purchase order status '{value}'")


def label(code: str) -> str:
    return LABELS[POStatus(code)]


def ensure_transition(current: str, new: POStatus) -> None:
    cur = POStatus(current)
    if new not in TRANSITIONS[cur]:
        raise ConflictError(f"Cannot move a purchase order from {LABELS[cur]} to {LABELS[new]}")


# Units on these POs count as "incoming" stock when calculating inventory position.
OPEN_STATUSES_FOR_INCOMING = (POStatus.DRAFT.value, POStatus.PENDING_APPROVAL.value, POStatus.APPROVED.value,
                              POStatus.ORDERED.value)

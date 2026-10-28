import pytest
from app.core.exceptions import BusinessRuleError, InvalidStateTransition
from app.models.entities import InventoryItem, POStatus, PurchaseOrder


def test_inventory_rules():
    item = InventoryItem(quantity_on_hand=10, safety_stock=2)
    assert item.remove(4) == 6
    with pytest.raises(BusinessRuleError):
        item.remove(100)
    with pytest.raises(BusinessRuleError):
        item.receive(0)


def test_purchase_order_state_machine():
    po = PurchaseOrder(product_id=1, supplier_id=1, quantity=5, unit_price=2.0)
    po.status = POStatus.PENDING_APPROVAL.value
    po.transition_to(POStatus.APPROVED)
    with pytest.raises(InvalidStateTransition):
        po.transition_to(POStatus.REJECTED)  # approved orders cannot be rejected
    po.transition_to(POStatus.RECEIVED)
    assert po.total_cost == 10.0

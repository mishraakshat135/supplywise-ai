"""Optional demo data mirroring frontend/src/services/mock/data.js, so the UI looks the same once connected.

Run:  python -m app.seed            (skips if products already exist)
      python -m app.seed --admin you@example.com --password 'a-strong-password'   (also creates an admin user)

The sales history is SYNTHETIC (generated here) so forecasting has something to learn from. Never use it as real data.
"""
import argparse
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from .core.actors import SYSTEM_ACTOR
from .core.security import hash_password
from .database.session import SessionLocal
from .models import (Product, PurchaseOrder, PurchaseOrderItem, Sale, Supplier, SupplierProduct, User)
from .services import audit, inventory_service as inv

# sku, name, category, stock, reorder, cost, preferred supplier, avg units/day
PRODUCTS = [
    ("EL-2048", "Industrial pressure sensor", "Electronics", 18, 30, 2480, "Northstar Components", 2.2),
    ("PK-1102", "Corrugated shipping carton", "Packaging", 420, 300, 42, "PackRight India", 15),
    ("MT-0815", "Stainless steel fastener M8", "Hardware", 64, 120, 18.5, "Metro Industrial", 9),
    ("EL-3091", "Motor control relay", "Electronics", 9, 24, 812, "Northstar Components", 1.4),
    ("CH-5530", "Food-grade cleaning solvent", "Chemicals", 145, 80, 295, "Apex ChemWorks", 3.5),
    ("PK-2214", "Pallet stretch film 500mm", "Packaging", 31, 60, 186, "PackRight India", 4.5),
    ("MT-0904", "Precision bearing 6204", "Hardware", 7, 20, 430, "Metro Industrial", 2.0),
    ("EL-4770", "24V power supply module", "Electronics", 52, 35, 1740, "CircuitSource", 2.5),
]
# code, name, categories, reliability %, availability, lead days, moq, price factor
SUPPLIERS = [
    ("SUP-014", "Northstar Components", ["Electronics", "Hardware"], 96, "Available", 5, 10, 1.00),
    ("SUP-027", "CircuitSource", ["Electronics"], 92, "Available", 9, 25, 0.95),
    ("SUP-031", "Metro Industrial", ["Hardware", "Electronics"], 98, "Limited", 3, 20, 1.05),
    ("SUP-006", "PackRight India", ["Packaging"], 94, "Available", 4, 100, 1.00),
    ("SUP-019", "Apex ChemWorks", ["Chemicals"], 89, "Available", 7, 12, 1.00),
]


def seed(db, admin_email=None, admin_password=None, days=120) -> str:
    if admin_email and admin_password and not db.scalar(select(User).where(User.email == admin_email)):
        db.add(User(email=admin_email, full_name="Admin", password_hash=hash_password(admin_password), role="admin"))
        db.commit()
    if db.scalar(select(Product).limit(1)):
        return "Products already exist, nothing seeded."
    rng = random.Random(42)
    suppliers = {}
    for code, name, cats, rel, avail, *_ in SUPPLIERS:
        s = Supplier(code=code, name=name, categories=cats, reliability=rel / 100, availability=avail)
        db.add(s)
        suppliers[name] = s
    db.flush()
    products = {}
    for sku, name, cat, stock, reorder, cost, sup, rate in PRODUCTS:
        p = inv.create_product(db, {"sku": sku, "name": name, "category": cat, "stock": stock, "reorder": reorder, "cost": cost,
                                    "supplier_id": suppliers[sup].id, "safety_stock": max(1, round(reorder * 0.4))}, SYSTEM_ACTOR)
        products[sku] = (p, rate)
    for code, name, cats, _, _, lead, moq, factor in SUPPLIERS:
        for sku, (p, _) in products.items():
            if p.category in cats:
                db.add(SupplierProduct(supplier_id=suppliers[name].id, product_id=p.id,
                                       unit_price=Decimal(str(round(float(p.unit_cost) * factor, 2))),
                                       lead_time_days=lead, moq=moq))
    today = date.today()
    for sku, (p, rate) in products.items():  # synthetic history with a weekly pattern and slow growth
        for d in range(days, 0, -1):
            day = today - timedelta(days=d)
            lam = rate * (1.2 if day.weekday() < 5 else 0.6) * (1 + 0.3 * (days - d) / days)
            q = max(0, round(rng.gauss(lam, lam ** 0.5)))
            if q:
                db.add(Sale(product_id=p.id, sale_date=day, quantity=q, unit_price=p.unit_cost))
    db.commit()
    # two historical purchase orders so the PO page is not empty (stock is NOT touched)
    for sku, sup, qty, status in (("PK-1102", "PackRight India", 500, "approved"), ("CH-5530", "Apex ChemWorks", 60, "ordered")):
        p = products[sku][0]
        offer = db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id == suppliers[sup].id, SupplierProduct.product_id == p.id))
        po = PurchaseOrder(supplier_id=suppliers[sup].id, status=status, total_cost=offer.unit_price * qty,
                           expected_delivery=today + timedelta(days=offer.lead_time_days))
        po.items = [PurchaseOrderItem(product_id=p.id, quantity=qty, unit_price=offer.unit_price)]
        db.add(po)
        db.flush()
        po.po_number = f"PO-{today.year}-{po.id:03d}"
        audit.log_action(db, "purchase_order", po.id, "created", SYSTEM_ACTOR, None, "draft")
        audit.log_action(db, "purchase_order", po.id, status, SYSTEM_ACTOR, "draft", status, "seed data")
    db.commit()
    return f"Seeded {len(PRODUCTS)} products, {len(SUPPLIERS)} suppliers, ~{days} days of synthetic sales."


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin")
    ap.add_argument("--password")
    a = ap.parse_args()
    with SessionLocal() as session:
        print(seed(session, a.admin, a.password))

"""Create a realistic demo dataset (categories, products, suppliers, 120 days of sales, policy doc).

Run from the project root:   python -m scripts.seed_demo_data
Safe to run once on an empty DB. Use --reset to wipe and recreate.

TODO(INTEGRATION: ML): replace the synthetic sales generator with a real dataset
(e.g. a Kaggle retail-sales CSV) via POST /sales/import-csv - the ML member can then
retrain with POST /forecasts/retrain.
"""
import argparse
import random
from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.models.entities import (Category, Document, InventoryItem, Product, SaleRecord, Supplier,
                                 SupplierProduct)
from app.rag.factory import get_retriever

POLICY = """Purchasing Policy v1.2

Orders with a total value above 50000 require written approval from the Operations Manager before
the purchase order is placed.

Preferred suppliers must have an on-time delivery rate above 90 percent. Suppliers below this level
need a documented justification.

Safety stock must cover at least 5 days of average demand for fast-moving electronics.

Contract terms - TechParts Ltd: lead time 3 days, minimum order quantity 50 units, 2 percent late
delivery penalty per day, payment terms net 30.

Contract terms - GlobalGadgets: lead time 7 days, minimum order quantity 100 units, free shipping
on orders above 20000.
"""


def main(reset: bool):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    random.seed(7)
    with SessionLocal() as db:
        if db.query(Product).count():
            print("Database already has data. Use --reset to recreate.")
            return
        cats = {n: Category(name=n) for n in ("Audio", "Computing", "Accessories")}
        db.add_all(cats.values())
        db.flush()

        # sku, name, category, price, cost, stock, safety, base daily demand
        catalog = [
            ("HP-100", "Wireless Headphones", "Audio", 80, 45, 30, 15, 12),
            ("SP-200", "Bluetooth Speaker", "Audio", 60, 32, 400, 20, 6),
            ("KB-300", "Mechanical Keyboard", "Computing", 90, 50, 120, 10, 5),
            ("MS-400", "Wireless Mouse", "Computing", 25, 12, 25, 10, 9),
            ("CB-500", "USB-C Cable", "Accessories", 8, 3, 900, 50, 20),
            ("NEW-600", "Noise-Cancelling Earbuds (new)", "Audio", 120, 70, 15, 5, 0),  # cold-start demo
        ]
        products = []
        for sku, name, cat, price, cost, stock, safety, base in catalog:
            p = Product(sku=sku, name=name, category_id=cats[cat].id, unit_price=price, unit_cost=cost)
            p.inventory = InventoryItem(quantity_on_hand=stock, safety_stock=safety)
            db.add(p)
            products.append((p, base))
        db.flush()

        today = date.today()
        for p, base in products:
            if base == 0:
                continue  # new product: no history
            for d in range(120, 0, -1):
                day = today - timedelta(days=d)
                weekend_boost = 1.3 if day.weekday() >= 5 else 1.0
                qty = max(0, int(random.gauss(base * weekend_boost, base * 0.25)))
                if qty:
                    db.add(SaleRecord(product_id=p.id, sale_date=day, quantity=qty, unit_price=p.unit_price))

        s1 = Supplier(name="TechParts Ltd", contact_email="sales@techparts.example", reliability_score=0.95)
        s2 = Supplier(name="GlobalGadgets", contact_email="orders@globalgadgets.example", reliability_score=0.88)
        s3 = Supplier(name="BudgetSource", contact_email="hello@budgetsource.example", reliability_score=0.80)
        db.add_all([s1, s2, s3])
        db.flush()
        for p, _ in products:
            c = p.unit_cost
            db.add_all([
                SupplierProduct(supplier_id=s1.id, product_id=p.id, unit_price=round(c * 1.05, 2), lead_time_days=3, min_order_qty=50),
                SupplierProduct(supplier_id=s2.id, product_id=p.id, unit_price=round(c * 0.98, 2), lead_time_days=7, min_order_qty=100),
                SupplierProduct(supplier_id=s3.id, product_id=p.id, unit_price=round(c * 0.92, 2), lead_time_days=12, min_order_qty=200),
            ])

        doc = Document(filename="purchasing_policy.txt", doc_type="policy", content=POLICY)
        db.add(doc)
        db.flush()
        doc.num_chunks = get_retriever().index_document(doc.id, doc.filename, POLICY)
        db.commit()
        print("Seeded demo data: 6 products, 3 suppliers, ~600 sales rows, 1 policy document.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    main(ap.parse_args().reset)

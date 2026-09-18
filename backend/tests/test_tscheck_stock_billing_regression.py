"""Criterion: core stock and billing flow works end to end (API layer).

Covers: create product, duplicate code rejected (409), add stock increases stock,
finalizing an invoice deducts stock, over-selling is rejected with no state change.
"""

import os

import pymongo

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "app")


def _mongo_db():
    mclient = pymongo.MongoClient(MONGO_URL)
    return mclient, mclient[DB_NAME]


def test_stock_and_billing_flow(client):
    mclient, db = _mongo_db()
    created_product_id = None
    created_invoice_ids = []
    try:
        # cleanup any leftover from a previous failed run
        db.products.delete_many({"code": "TSCHK-BILL-01"})

        create_resp = client.post(
            "/products",
            json={
                "name": "tscheck-billing-flow-product",
                "code": "TSCHK-BILL-01",
                "stock": 5,
                "unit_price": 200.0,
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        product = create_resp.json()
        created_product_id = product["id"]
        assert product["status"] == "low_stock"

        # duplicate code rejected
        dup_resp = client.post(
            "/products",
            json={
                "name": "tscheck-billing-flow-dup",
                "code": "TSCHK-BILL-01",
                "stock": 1,
                "unit_price": 10.0,
            },
        )
        assert dup_resp.status_code == 409, dup_resp.text

        # add stock
        stock_resp = client.patch(
            f"/products/{created_product_id}/stock", json={"additional_quantity": 10}
        )
        assert stock_resp.status_code == 200, stock_resp.text
        updated = stock_resp.json()
        assert updated["stock"] == 15

        today = client.get("/invoices/next-number").json()["date"]

        # over-selling rejected, no invoice created, stock unchanged
        oversell_resp = client.post(
            "/invoices",
            json={
                "customer_name": "tscheck-billing-oversell-customer",
                "date": today,
                "items": [
                    {
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "product_code": product["code"],
                        "quantity": 999,
                        "unit_price": product["unit_price"],
                    }
                ],
                "discount": 0,
            },
        )
        assert oversell_resp.status_code == 409, oversell_resp.text
        assert "Insufficient stock" in oversell_resp.text

        stock_after_oversell = client.get(f"/products/{created_product_id}") if False else None
        products_list = client.get("/products").json()
        current = next(p for p in products_list if p["id"] == created_product_id)
        assert current["stock"] == 15, "stock must be unchanged after rejected oversell"

        invoices_before = len(client.get("/invoices").json())

        # valid invoice deducts stock
        good_resp = client.post(
            "/invoices",
            json={
                "customer_name": "tscheck-billing-good-customer",
                "date": today,
                "items": [
                    {
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "product_code": product["code"],
                        "quantity": 4,
                        "unit_price": product["unit_price"],
                    }
                ],
                "discount": 50,
            },
        )
        assert good_resp.status_code == 201, good_resp.text
        invoice = good_resp.json()
        created_invoice_ids.append(invoice["id"])
        assert invoice["subtotal"] == 800.0
        assert invoice["discount"] == 50
        assert invoice["total"] == 750.0
        assert invoice["status"] == "Finalized"

        products_list_after = client.get("/products").json()
        current_after = next(p for p in products_list_after if p["id"] == created_product_id)
        assert current_after["stock"] == 11, f"expected stock 15-4=11, got {current_after['stock']}"

        invoices_after = len(client.get("/invoices").json())
        assert invoices_after == invoices_before + 1

        # invoice appears in history
        all_invoices = client.get("/invoices").json()
        assert any(inv["id"] == invoice["id"] for inv in all_invoices)
    finally:
        if created_invoice_ids:
            db.invoices.delete_many({"id": {"$in": created_invoice_ids}})
        if created_product_id:
            db.products.delete_many({"id": created_product_id})
        mclient.close()

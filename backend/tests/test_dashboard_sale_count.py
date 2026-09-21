"""Dashboard sale count must sum invoice item quantities, not invoice count."""

import os

import pymongo

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "app")


def _mongo_db():
    mclient = pymongo.MongoClient(MONGO_URL)
    return mclient, mclient[DB_NAME]


def test_dashboard_sale_count_sums_invoice_quantities(client):
    mclient, db = _mongo_db()
    created_product_ids = []
    created_invoice_ids = []
    try:
        db.products.delete_many({"code": {"$in": ["TSCHK-DASH-01", "TSCHK-DASH-02"]}})

        products = []
        for code in ("TSCHK-DASH-01", "TSCHK-DASH-02"):
            response = client.post(
                "/products",
                json={"name": code, "code": code, "stock": 20, "unit_price": 10},
            )
            assert response.status_code == 201, response.text
            product = response.json()
            products.append(product)
            created_product_ids.append(product["id"])

        today = client.get("/invoices/next-number").json()["date"]
        before = client.get("/dashboard")
        assert before.status_code == 200, before.text
        before_summary = before.json()

        response = client.post(
            "/invoices",
            json={
                "customer_name": "tscheck-dashboard-sale-count",
                "date": today,
                "payment_method": "Cash",
                "items": [
                    {"product_id": products[0]["id"], "quantity": 3},
                    {"product_id": products[1]["id"], "quantity": 5},
                ],
                "discount": 0,
            },
        )
        assert response.status_code == 201, response.text
        created_invoice_ids.append(response.json()["id"])

        after = client.get("/dashboard")
        assert after.status_code == 200, after.text
        after_summary = after.json()
        assert after_summary["today_invoice_count"] == before_summary["today_invoice_count"] + 1
        assert after_summary["sale_count"] == before_summary["sale_count"] + 8
    finally:
        if created_invoice_ids:
            db.invoices.delete_many({"id": {"$in": created_invoice_ids}})
        if created_product_ids:
            db.products.delete_many({"id": {"$in": created_product_ids}})
        mclient.close()

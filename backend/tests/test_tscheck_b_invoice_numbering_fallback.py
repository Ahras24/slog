"""Criterion: numbering falls back after deletions rather than climbing forever.

Creates two fixture invoices, deletes the highest-numbered one directly via MongoDB
(no DELETE endpoint exists by design), and verifies GET /invoices/next-number reports
that freed number again and the next finalized invoice reuses it with no duplicates.
"""

import os
import re

import pymongo

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "app")


def _mongo_db():
    mclient = pymongo.MongoClient(MONGO_URL)
    return mclient, mclient[DB_NAME]


def _seq(invoice_number: str) -> int:
    m = re.search(r"(\d+)$", invoice_number)
    return int(m.group(1)) if m else -1


def _get_or_create_product(client):
    resp = client.post(
        "/products",
        json={
            "name": "tscheck-numbering-fallback-product",
            "code": "TSCHK-NUMR-02",
            "stock": 50,
            "unit_price": 50.0,
        },
    )
    if resp.status_code == 409:
        existing = client.get("/products").json()
        return next(p for p in existing if p["code"] == "TSCHK-NUMR-02")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_invoice(client, product, customer_suffix, date):
    resp = client.post(
        "/invoices",
        json={
            "customer_name": f"tscheck-numbering-fallback-{customer_suffix}",
            "date": date,
            "items": [
                {
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "product_code": product["code"],
                    "quantity": 1,
                    "unit_price": product["unit_price"],
                }
            ],
            "discount": 0,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_numbering_falls_back_after_db_deletion(client):
    mclient, db = _mongo_db()
    created_ids = []
    try:
        product = _get_or_create_product(client)
        today = client.get("/invoices/next-number").json()["date"]

        inv_a = _create_invoice(client, product, "a", today)
        created_ids.append(inv_a["id"])
        inv_b = _create_invoice(client, product, "b", today)
        created_ids.append(inv_b["id"])

        assert _seq(inv_b["invoice_number"]) == _seq(inv_a["invoice_number"]) + 1

        # delete the highest-numbered invoice directly via MongoDB
        highest = inv_b if _seq(inv_b["invoice_number"]) > _seq(inv_a["invoice_number"]) else inv_a
        lower = inv_a if highest is inv_b else inv_b
        del_result = db.invoices.delete_one({"id": highest["id"]})
        assert del_result.deleted_count == 1
        created_ids.remove(highest["id"])

        # next-number should now report the freed number again
        preview = client.get("/invoices/next-number").json()
        assert preview["invoice_number"] == highest["invoice_number"], (
            f"Expected numbering to fall back to {highest['invoice_number']}, "
            f"got {preview['invoice_number']}"
        )

        # finalize a new invoice -> it must reuse the freed number
        inv_c = _create_invoice(client, product, "c", today)
        created_ids.append(inv_c["id"])
        assert inv_c["invoice_number"] == highest["invoice_number"]

        # no duplicate invoice_number exists among current invoices
        all_invoices = client.get("/invoices").json()
        numbers = [inv["invoice_number"] for inv in all_invoices]
        assert len(numbers) == len(set(numbers)), "Duplicate invoice_number detected"

        # sanity: lower's number untouched and distinct from reused one
        assert lower["invoice_number"] != inv_c["invoice_number"]
    finally:
        if created_ids:
            db.invoices.delete_many({"id": {"$in": created_ids}})
        db.products.delete_many({"code": "TSCHK-NUMR-02"})
        mclient.close()

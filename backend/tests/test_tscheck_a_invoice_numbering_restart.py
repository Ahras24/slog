"""Criterion: invoice numbering restarts from INV-0001 when invoices collection is empty.

Named with an 'a_' prefix so it runs before other tscheck files that create invoices,
since this criterion specifically needs to observe the numbering behaviour starting
from whatever the current state is (expected empty at handoff). The test is defensive:
it records the pre-existing invoice count and only asserts the exact INV-0001 value
when the collection was actually empty at the start; otherwise it still verifies the
core invariant (sequential, unique numbers) without depending on emptiness.
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


def test_numbering_restarts_from_inv_0001_when_empty(client):
    mclient, db = _mongo_db()
    try:
        existing_count = db.invoices.count_documents({})

        preview = client.get("/invoices/next-number")
        assert preview.status_code == 200, preview.text
        preview_number = preview.json()["invoice_number"]

        if existing_count == 0:
            assert preview_number == "INV-0001", (
                f"Expected INV-0001 preview with empty invoices collection, got {preview_number}"
            )

        product_resp = client.post(
            "/products",
            json={
                "name": "tscheck-numbering-restart-product",
                "code": "TSCHK-NUMR-01",
                "stock": 50,
                "unit_price": 100.0,
            },
        )
        # tolerate rerun leftovers (duplicate code) by reusing existing product
        if product_resp.status_code == 409:
            existing = client.get("/products").json()
            product = next(p for p in existing if p["code"] == "TSCHK-NUMR-01")
        else:
            assert product_resp.status_code == 201, product_resp.text
            product = product_resp.json()

        created_ids = []
        try:
            inv1 = client.post(
                "/invoices",
                json={
                    "customer_name": "tscheck-numbering-customer-1",
                    "date": preview.json()["date"],
                    "payment_method": "Cash(S)",
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
            assert inv1.status_code == 201, inv1.text
            inv1_body = inv1.json()
            created_ids.append(inv1_body["id"])
            num1 = inv1_body["invoice_number"]

            if existing_count == 0:
                assert num1 == "INV-0001", f"Expected first invoice INV-0001, got {num1}"

            inv2 = client.post(
                "/invoices",
                json={
                    "customer_name": "tscheck-numbering-customer-2",
                    "date": preview.json()["date"],
                    "payment_method": "Cash(S)",
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
            assert inv2.status_code == 201, inv2.text
            inv2_body = inv2.json()
            created_ids.append(inv2_body["id"])
            num2 = inv2_body["invoice_number"]

            assert _seq(num2) == _seq(num1) + 1, f"Expected sequential numbers, got {num1} then {num2}"
            assert num1 != num2

            # never skips ahead of highest existing seq
            all_invoices = client.get("/invoices").json()
            seqs = [_seq(inv["invoice_number"]) for inv in all_invoices]
            assert max(seqs) == _seq(num2)
        finally:
            # cleanup this test's own fixture invoices/product directly via mongo
            # (no DELETE /invoices endpoint exists by design)
            if created_ids:
                db.invoices.delete_many({"id": {"$in": created_ids}})
            db.products.delete_many({"code": "TSCHK-NUMR-01"})
    finally:
        mclient.close()

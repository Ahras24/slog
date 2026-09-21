"""Invoice history pagination is applied by the API and database query."""

import os

import pymongo

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "app")


def _mongo_db():
    mclient = pymongo.MongoClient(MONGO_URL)
    return mclient, mclient[DB_NAME]


def test_invoice_history_paginates_and_filters(client):
    mclient, db = _mongo_db()
    prefix = "tscheck-pagination"
    product_id = None
    invoice_ids = []
    try:
        existing_product = next(
            (product for product in client.get("/products").json() if product["code"] == "TSCHK-PAGE-01"),
            None,
        )
        if existing_product:
            client.delete(f"/products/{existing_product['id']}")
        product_response = client.post(
            "/products",
            json={"name": prefix, "code": "TSCHK-PAGE-01", "stock": 21, "unit_price": 10},
        )
        assert product_response.status_code == 201, product_response.text
        product_id = product_response.json()["id"]

        for index in range(21):
            invoice_response = client.post(
                "/invoices",
                json={
                    "customer_name": f"{prefix}-{index + 1:02d}",
                    "payment_method": "Cash",
                    "items": [{"product_id": product_id, "quantity": 1}],
                    "discount": 0,
                },
            )
            assert invoice_response.status_code == 201, invoice_response.text
            invoice_ids.append(invoice_response.json()["id"])

        empty = client.get("/invoices", params={"search": "does-not-exist"})
        assert empty.status_code == 200, empty.text
        assert empty.json() == {"invoices": [], "page": 1, "limit": 10, "total": 0, "total_pages": 0}

        page_one = client.get("/invoices", params={"search": prefix, "page": 1, "limit": 10})
        assert page_one.status_code == 200, page_one.text
        page_one_body = page_one.json()
        assert page_one_body["total"] == 21
        assert page_one_body["total_pages"] == 3
        assert len(page_one_body["invoices"]) == 10
        assert page_one_body["invoices"][0]["customer_name"] == f"{prefix}-21"

        page_two = client.get("/invoices", params={"search": prefix, "page": 2, "limit": 10})
        assert len(page_two.json()["invoices"]) == 10

        page_three = client.get("/invoices", params={"search": prefix, "page": 3, "limit": 10})
        assert len(page_three.json()["invoices"]) == 1
        assert page_three.json()["invoices"][0]["customer_name"] == f"{prefix}-01"
    finally:
        for invoice_id in invoice_ids:
            client.delete(f"/invoices/{invoice_id}")
        if product_id:
            db.products.delete_one({"id": product_id})
        mclient.close()
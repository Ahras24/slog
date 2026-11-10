"""Deleting invoices restores stock and removes invoice-backed sales."""

import os
from datetime import datetime, time, timedelta, timezone
from uuid import uuid4

import pymongo
import pytest

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "app")


def _mongo_db():
    mclient = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=1000)
    return mclient, mclient[DB_NAME]


def _delete_products(client, products):
    for product in products:
        client.delete(f"/products/{product['id']}")


def _create_product(client, code, stock, price):
    response = client.post(
        "/products",
        json={"name": code, "code": code, "stock": stock, "unit_price": price},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_delete_invoice_restores_stock_and_reverses_sales(client):
    suffix = uuid4().hex[:8].upper()
    products = []
    invoice_ids = []
    try:
        products = [
            _create_product(client, f"DEL-{suffix}-{index}", 20, (index + 1) * 10)
            for index in range(3)
        ]
        today = client.get("/invoices/next-number").json()["date"]
        before_dashboard = client.get("/dashboard").json()
        before_daily = client.get("/reports/stock-sales", params={"date": today}).json()
        before_monthly = client.get("/reports/stock-sales", params={"month": today[:7]}).json()

        multi_response = client.post(
            "/invoices",
            json={
                "customer_name": f"delete-multi-{suffix}",
                "payment_method": "Cash(A)",
                "advance_amount": 140,
                "items": [
                    {"product_id": products[0]["id"], "quantity": 2},
                    {"product_id": products[1]["id"], "quantity": 5},
                    {"product_id": products[2]["id"], "quantity": 1},
                ],
                "discount": 10,
            },
        )
        assert multi_response.status_code == 201, multi_response.text
        multi_invoice = multi_response.json()
        invoice_ids.append(multi_invoice["id"])

        single_response = client.post(
            "/invoices",
            json={
                "customer_name": f"delete-single-{suffix}",
                "payment_method": "Cash(Z)",
                "advance_amount": 10,
                "items": [{"product_id": products[0]["id"], "quantity": 1}],
                "discount": 0,
            },
        )
        assert single_response.status_code == 201, single_response.text
        single_invoice = single_response.json()
        invoice_ids.append(single_invoice["id"])

        current_products = {product["id"]: product for product in client.get("/products").json()}
        assert [current_products[product["id"]]["stock"] for product in products] == [17, 15, 19]

        after_dashboard = client.get("/dashboard").json()
        assert after_dashboard["total_products"] == before_dashboard["total_products"]
        assert after_dashboard["today_invoice_count"] == before_dashboard["today_invoice_count"] + 2
        assert after_dashboard["sale_count"] == before_dashboard["sale_count"] + 9
        assert after_dashboard["today_sales"] == before_dashboard["today_sales"] + multi_invoice["total"] + single_invoice["total"]
        assert after_dashboard["total_stock"] == before_dashboard["total_stock"] - 9

        after_daily = client.get("/reports/stock-sales", params={"date": today}).json()
        after_monthly = client.get("/reports/stock-sales", params={"month": today[:7]}).json()
        for report, baseline in ((after_daily, before_daily), (after_monthly, before_monthly)):
            assert report["summary"]["total_stock_received"] == baseline["summary"]["total_stock_received"]
            assert report["summary"]["total_units_sold"] == baseline["summary"]["total_units_sold"] + 9
            assert report["summary"]["total_sales_amount"] == baseline["summary"]["total_sales_amount"] + 150
            assert report["summary"]["products_sold"] == baseline["summary"]["products_sold"] + 3

        deleted = client.delete(f"/invoices/{multi_invoice['id']}")
        assert deleted.status_code == 204, deleted.text
        current_products = {product["id"]: product for product in client.get("/products").json()}
        assert [current_products[product["id"]]["stock"] for product in products] == [19, 20, 20]
        after_first_delete = client.get("/dashboard").json()
        assert after_first_delete["total_stock"] == before_dashboard["total_stock"] - 1
        assert after_first_delete["today_invoice_count"] == before_dashboard["today_invoice_count"] + 1
        assert after_first_delete["sale_count"] == before_dashboard["sale_count"] + 1
        after_first_report = client.get("/reports/stock-sales", params={"month": today[:7]}).json()
        assert after_first_report["summary"]["total_stock_received"] == before_monthly["summary"]["total_stock_received"]
        assert after_first_report["summary"]["total_units_sold"] == before_monthly["summary"]["total_units_sold"] + 1
        assert after_first_report["summary"]["total_sales_amount"] == before_monthly["summary"]["total_sales_amount"] + single_invoice["total"]
        assert after_first_report["summary"]["products_sold"] == before_monthly["summary"]["products_sold"] + 1

        deleted = client.delete(f"/invoices/{single_invoice['id']}")
        assert deleted.status_code == 204, deleted.text
        current_products = {product["id"]: product for product in client.get("/products").json()}
        assert [current_products[product["id"]]["stock"] for product in products] == [20, 20, 20]
        after_dashboard = client.get("/dashboard").json()
        assert after_dashboard == before_dashboard
        assert after_dashboard["total_products"] == before_dashboard["total_products"]
        assert client.get("/reports/stock-sales", params={"date": today}).json() == before_daily
        assert client.get("/reports/stock-sales", params={"month": today[:7]}).json() == before_monthly

        repeated_delete = client.delete(f"/invoices/{multi_invoice['id']}")
        assert repeated_delete.status_code == 404
        current_products = {product["id"]: product for product in client.get("/products").json()}
        assert [current_products[product["id"]]["stock"] for product in products] == [20, 20, 20]
    finally:
        for invoice_id in invoice_ids:
            client.delete(f"/invoices/{invoice_id}")
        _delete_products(client, products)


def test_delete_historical_invoice_removes_historical_report_sales(client):
    mongo_client, db = _mongo_db()
    try:
        mongo_client.admin.command("ping")
    except pymongo.errors.ServerSelectionTimeoutError:
        mongo_client.close()
        pytest.skip("Historical invoice setup requires direct MongoDB access.")

    suffix = uuid4().hex[:8].upper()
    product = None
    invoice_id = None
    try:
        product = _create_product(client, f"DEL-HIST-{suffix}", 10, 25)
        today = datetime.strptime(client.get("/invoices/next-number").json()["date"], "%Y-%m-%d").date()
        historical_date = (today - timedelta(days=1)).isoformat()
        before_report = client.get(
            "/reports/stock-sales", params={"date": historical_date}
        ).json()["summary"]
        historical_month = historical_date[:7]
        before_monthly = client.get(
            "/reports/stock-sales", params={"month": historical_month}
        ).json()["summary"]

        response = client.post(
            "/invoices",
            json={
                "customer_name": f"delete-history-{suffix}",
                "payment_method": "Cash(I)",
                "advance_amount": 75,
                "items": [{"product_id": product["id"], "quantity": 3}],
                "discount": 0,
            },
        )
        assert response.status_code == 201, response.text
        invoice_id = response.json()["id"]

        historical_timestamp = datetime.combine(
            today - timedelta(days=1),
            time(6, 30),
            tzinfo=timezone.utc,
        )
        db.invoices.update_one({"id": invoice_id}, {"$set": {"date": historical_date}})
        db.stock_transactions.update_many(
            {"reference_id": invoice_id, "transaction_type": "sold"},
            {"$set": {"created_at": historical_timestamp}},
        )

        historical_report = client.get(
            "/reports/stock-sales", params={"date": historical_date}
        ).json()["summary"]
        historical_monthly = client.get(
            "/reports/stock-sales", params={"month": historical_month}
        ).json()["summary"]
        assert historical_report["total_units_sold"] == before_report["total_units_sold"] + 3
        assert historical_report["total_sales_amount"] == before_report["total_sales_amount"] + 75
        assert historical_monthly["total_units_sold"] == before_monthly["total_units_sold"] + 3
        assert historical_monthly["total_sales_amount"] == before_monthly["total_sales_amount"] + 75

        deleted = client.delete(f"/invoices/{invoice_id}")
        assert deleted.status_code == 204, deleted.text
        assert client.get("/reports/stock-sales", params={"date": historical_date}).json()["summary"] == before_report
        assert client.get("/reports/stock-sales", params={"month": historical_month}).json()["summary"] == before_monthly
        restored = next(item for item in client.get("/products").json() if item["id"] == product["id"])
        assert restored["stock"] == 10
    finally:
        if invoice_id:
            client.delete(f"/invoices/{invoice_id}")
        if product:
            _delete_products(client, [product])
        mongo_client.close()


def test_delete_invoice_succeeds_when_a_product_was_removed(client):
    suffix = uuid4().hex[:8].upper()
    product = _create_product(client, f"DEL-MISSING-{suffix}", 5, 15)
    invoice_id = None
    try:
        response = client.post(
            "/invoices",
            json={
                "customer_name": f"delete-missing-{suffix}",
                "payment_method": "Cash(S)",
                "items": [{"product_id": product["id"], "quantity": 2}],
                "discount": 0,
            },
        )
        assert response.status_code == 201, response.text
        invoice_id = response.json()["id"]
        assert client.delete(f"/products/{product['id']}").status_code == 204

        deleted = client.delete(f"/invoices/{invoice_id}")
        assert deleted.status_code == 204, deleted.text
        assert client.delete(f"/invoices/{invoice_id}").status_code == 404
    finally:
        if invoice_id:
            client.delete(f"/invoices/{invoice_id}")
        client.delete(f"/products/{product['id']}")


def test_gst_is_optional_and_included_in_invoice_and_sales_report(client):
    suffix = uuid4().hex[:8].upper()
    product = _create_product(client, f"DEL-GST-{suffix}", 10, 100)
    invoice_id = None
    try:
        today = client.get("/invoices/next-number").json()["date"]
        before_dashboard = client.get("/dashboard").json()
        before_report = client.get("/reports/stock-sales", params={"month": today[:7]}).json()

        response = client.post(
            "/invoices",
            json={
                "customer_name": f"gst-customer-{suffix}",
                "payment_method": "Cash",
                "advance_amount": 189,
                "items": [{"product_id": product["id"], "quantity": 2}],
                "discount": 20,
                "gst_enabled": True,
            },
        )
        assert response.status_code == 201, response.text
        invoice = response.json()
        invoice_id = invoice["id"]
        assert invoice["subtotal"] == 200
        assert invoice["discount"] == 20
        assert invoice["gst_enabled"] is True
        assert invoice["gst_amount"] == 9
        assert invoice["total"] == 189

        after_dashboard = client.get("/dashboard").json()
        assert after_dashboard["today_sales"] == before_dashboard["today_sales"] + 189
        after_report = client.get("/reports/stock-sales", params={"month": today[:7]}).json()
        assert after_report["summary"]["total_sales_amount"] == before_report["summary"]["total_sales_amount"] + 189
        assert after_report["summary"]["total_units_sold"] == before_report["summary"]["total_units_sold"] + 2

        deleted = client.delete(f"/invoices/{invoice_id}")
        assert deleted.status_code == 204, deleted.text
        invoice_id = None
        assert client.get("/dashboard").json() == before_dashboard
        assert client.get("/reports/stock-sales", params={"month": today[:7]}).json() == before_report
        restored = next(item for item in client.get("/products").json() if item["id"] == product["id"])
        assert restored["stock"] == 10
    finally:
        if invoice_id:
            client.delete(f"/invoices/{invoice_id}")
        _delete_products(client, [product])

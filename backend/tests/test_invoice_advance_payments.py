"""Pending invoices deduct stock immediately and enter sales only when fully paid."""

from uuid import uuid4


def test_advance_payment_workflow_and_status_filters(client):
    suffix = uuid4().hex[:8]
    product = None
    invoice_ids = []
    try:
        product_response = client.post(
            "/products",
            json={"name": f"ADV-{suffix}", "code": f"ADV-{suffix}", "stock": 50, "unit_price": 100},
        )
        assert product_response.status_code == 201, product_response.text
        product = product_response.json()

        today = client.get("/invoices/next-number").json()["date"]
        before_dashboard = client.get("/dashboard").json()
        before_report = client.get("/reports/stock-sales", params={"month": today[:7]}).json()

        def create_invoice(name, quantity, advance, payment_method):
            response = client.post(
                "/invoices",
                json={
                    "customer_name": f"ADV-{suffix}-{name}",
                    "payment_method": payment_method,
                    "advance_amount": advance,
                    "request_id": str(uuid4()),
                    "items": [{"product_id": product["id"], "quantity": quantity}],
                },
            )
            assert response.status_code == 201, response.text
            invoice = response.json()
            invoice_ids.append(invoice["id"])
            return invoice

        zero_advance = create_invoice("zero", 1, 0, "Cash(S)")
        retried_zero = client.post(
            "/invoices",
            json={
                "customer_name": f"ADV-{suffix}-zero",
                "payment_method": "Cash(S)",
                "advance_amount": 0,
                "request_id": zero_advance["request_id"],
                "items": [{"product_id": product["id"], "quantity": 1}],
            },
        )
        assert retried_zero.status_code == 201, retried_zero.text
        assert retried_zero.json()["id"] == zero_advance["id"]
        partial = create_invoice("partial", 2, 50, "Cash(A)")
        fully_paid = create_invoice("full", 1, 100, "Cash(I)")

        assert zero_advance["status"] == "Pending"
        assert zero_advance["total_paid"] == 0
        assert zero_advance["remaining_balance"] == 100
        assert zero_advance["payments"] == []
        assert partial["status"] == "Pending"
        assert partial["total_paid"] == 50
        assert partial["remaining_balance"] == 150
        assert len(partial["payments"]) == 1
        assert fully_paid["status"] == "Finalized"
        assert fully_paid["remaining_balance"] == 0

        current_product = next(item for item in client.get("/products").json() if item["id"] == product["id"])
        assert current_product["stock"] == 46

        after_creation = client.get("/dashboard").json()
        assert after_creation["total_stock"] == before_dashboard["total_stock"] - 4
        assert after_creation["today_sales"] == before_dashboard["today_sales"] + 100
        assert after_creation["today_invoice_count"] == before_dashboard["today_invoice_count"] + 1
        assert after_creation["sale_count"] == before_dashboard["sale_count"] + 1

        after_creation_report = client.get("/reports/stock-sales", params={"month": today[:7]}).json()
        assert after_creation_report["summary"]["total_stock_received"] == before_report["summary"]["total_stock_received"]
        assert after_creation_report["summary"]["total_units_sold"] == before_report["summary"]["total_units_sold"] + 1
        assert after_creation_report["summary"]["total_sales_amount"] == before_report["summary"]["total_sales_amount"] + 100
        product_report = next(row for row in after_creation_report["products"] if row["product_id"] == product["id"])
        assert product_report["closing_stock"] == 46
        assert product_report["sold_quantity"] == 1

        all_invoices = client.get("/invoices", params={"search": f"ADV-{suffix}"}).json()
        pending_invoices = client.get(
            "/invoices", params={"search": f"ADV-{suffix}", "status": "pending"}
        ).json()
        finalized_invoices = client.get(
            "/invoices", params={"search": f"ADV-{suffix}", "status": "finalized"}
        ).json()
        assert all_invoices["total"] == 3
        assert pending_invoices["total"] == 2
        assert finalized_invoices["total"] == 1

        payment_one_id = str(uuid4())
        payment_one = {
            "id": payment_one_id,
            "amount": 75,
            "payment_method": "Cash(Z)",
        }
        added_payment = client.post(f"/invoices/{partial['id']}/payments", json=payment_one)
        assert added_payment.status_code == 200, added_payment.text
        still_pending = added_payment.json()
        assert still_pending["status"] == "Pending"
        assert still_pending["total_paid"] == 125
        assert still_pending["remaining_balance"] == 75

        repeated_payment = client.post(f"/invoices/{partial['id']}/payments", json=payment_one)
        assert repeated_payment.status_code == 200, repeated_payment.text
        assert len(repeated_payment.json()["payments"]) == 2
        excess_payment = client.post(
            f"/invoices/{partial['id']}/payments",
            json={"id": str(uuid4()), "amount": 76, "payment_method": "Cash"},
        )
        assert excess_payment.status_code == 400
        zero_payment = client.post(
            f"/invoices/{partial['id']}/payments",
            json={"id": str(uuid4()), "amount": 0, "payment_method": "Cash"},
        )
        assert zero_payment.status_code == 422

        final_payment = client.post(
            f"/invoices/{partial['id']}/payments",
            json={"id": str(uuid4()), "amount": 75, "payment_method": "Cash"},
        )
        assert final_payment.status_code == 200, final_payment.text
        finalized_partial = final_payment.json()
        assert finalized_partial["status"] == "Finalized"
        assert finalized_partial["total_paid"] == finalized_partial["total"]
        assert finalized_partial["remaining_balance"] == 0
        assert len(finalized_partial["payments"]) == 3

        after_payment_dashboard = client.get("/dashboard").json()
        assert after_payment_dashboard["total_stock"] == after_creation["total_stock"]
        assert after_payment_dashboard["today_sales"] == before_dashboard["today_sales"] + 300
        assert after_payment_dashboard["today_invoice_count"] == before_dashboard["today_invoice_count"] + 2
        assert after_payment_dashboard["sale_count"] == before_dashboard["sale_count"] + 3

        after_payment_report = client.get("/reports/stock-sales", params={"month": today[:7]}).json()
        assert after_payment_report["summary"]["total_stock_received"] == before_report["summary"]["total_stock_received"]
        assert after_payment_report["summary"]["total_units_sold"] == before_report["summary"]["total_units_sold"] + 3
        assert after_payment_report["summary"]["total_sales_amount"] == before_report["summary"]["total_sales_amount"] + 300
        product_report = next(row for row in after_payment_report["products"] if row["product_id"] == product["id"])
        assert product_report["closing_stock"] == 46
        assert product_report["sold_quantity"] == 3

        assert client.get(
            "/invoices", params={"search": f"ADV-{suffix}", "status": "pending"}
        ).json()["total"] == 1
        assert client.get(
            "/invoices", params={"search": f"ADV-{suffix}", "status": "finalized"}
        ).json()["total"] == 2

        assert client.delete(f"/invoices/{zero_advance['id']}").status_code == 204
        assert client.get("/dashboard").json()["today_sales"] == after_payment_dashboard["today_sales"]
        assert client.delete(f"/invoices/{finalized_partial['id']}").status_code == 204
        assert client.delete(f"/invoices/{fully_paid['id']}").status_code == 204

        assert client.get("/dashboard").json() == before_dashboard
        assert client.get("/reports/stock-sales", params={"month": today[:7]}).json() == before_report
        restored_product = next(item for item in client.get("/products").json() if item["id"] == product["id"])
        assert restored_product["stock"] == 50
    finally:
        for invoice_id in invoice_ids:
            client.delete(f"/invoices/{invoice_id}")
        if product is not None:
            client.delete(f"/products/{product['id']}")

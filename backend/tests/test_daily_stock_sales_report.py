"""Daily stock and sales reports use transactions and invoice snapshots."""

def test_daily_stock_sales_report_uses_daily_movements_and_invoice_prices(client):
    product_id = None
    invoice_ids = []
    report_date = client.get("/invoices/next-number").json()["date"]
    code = "TSCHK-DAILY-01"
    try:
        product_response = client.post(
            "/products",
            json={"name": "daily-report-product", "code": code, "stock": 0, "unit_price": 200},
        )
        if product_response.status_code == 409:
            existing = next(product for product in client.get("/products").json() if product["code"] == code)
            client.delete(f"/products/{existing['id']}")
            product_response = client.post(
                "/products",
                json={"name": "daily-report-product", "code": code, "stock": 0, "unit_price": 200},
            )
        assert product_response.status_code == 201, product_response.text
        product_id = product_response.json()["id"]

        before_report = client.get("/reports/stock-sales", params={"date": report_date})
        assert before_report.status_code == 200, before_report.text
        before_summary = before_report.json()["summary"]

        received_response = client.patch(f"/products/{product_id}/stock", json={"additional_quantity": 20})
        assert received_response.status_code == 200, received_response.text

        for customer, quantity in (("daily-customer-one", 3), ("daily-customer-two", 2)):
            invoice_response = client.post(
                "/invoices",
                json={
                    "customer_name": customer,
                    "date": report_date,
                    "payment_method": "Cash",
                    "items": [{"product_id": product_id, "quantity": quantity, "unit_price": 250}],
                    "discount": 0,
                },
            )
            assert invoice_response.status_code == 201, invoice_response.text
            invoice_ids.append(invoice_response.json()["id"])

        report_response = client.get("/reports/stock-sales", params={"date": report_date})
        assert report_response.status_code == 200, report_response.text
        data = report_response.json()
        assert data["report_type"] == "daily"
        assert data["selected_date"] == report_date
        assert data["summary"]["total_stock_received"] == before_summary["total_stock_received"] + 20
        assert data["summary"]["total_units_sold"] == before_summary["total_units_sold"] + 5
        assert data["summary"]["total_sales_amount"] == before_summary["total_sales_amount"] + 1250.0
        assert data["summary"]["products_sold"] == before_summary["products_sold"] + 1
        row = next(product for product in data["products"] if product["product_code"] == code)
        assert row["opening_stock"] == 0
        assert row["stock_received"] == 20
        assert row["sold_quantity"] == 5
        assert row["closing_stock"] == 15
        assert row["sales_amount"] == 1250.0

        empty_day = client.get("/reports/stock-sales", params={"date": "2000-01-01"})
        assert empty_day.status_code == 200, empty_day.text
        empty_row = next(product for product in empty_day.json()["products"] if product["product_code"] == code)
        assert empty_day.json()["summary"]["total_units_sold"] == 0
        assert empty_row["sold_quantity"] == 0
    finally:
        for invoice_id in invoice_ids:
            client.delete(f"/invoices/{invoice_id}")
        if product_id:
            client.delete(f"/products/{product_id}")

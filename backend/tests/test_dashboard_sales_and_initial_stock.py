"""Dashboard net sales and initial product stock are reflected in reports."""


def test_dashboard_net_sales_and_initial_stock(client):
    code = "TSCHK-INITIAL-01"
    product_id = None
    invoice_id = None
    try:
        product_response = client.post(
            "/products",
            json={"name": "initial-stock-report-product", "code": code, "stock": 20, "unit_price": 100},
        )
        if product_response.status_code == 409:
            existing = next(product for product in client.get("/products").json() if product["code"] == code)
            client.delete(f"/products/{existing['id']}")
            product_response = client.post(
                "/products",
                json={"name": "initial-stock-report-product", "code": code, "stock": 20, "unit_price": 100},
            )
        assert product_response.status_code == 201, product_response.text
        product_id = product_response.json()["id"]

        today = client.get("/invoices/next-number").json()["date"]
        before_dashboard = client.get("/dashboard").json()
        before_report = client.get("/reports/stock-sales", params={"date": today}).json()

        add_stock_response = client.patch(f"/products/{product_id}/stock", json={"additional_quantity": 5})
        assert add_stock_response.status_code == 200, add_stock_response.text

        invoice_response = client.post(
            "/invoices",
            json={
                "customer_name": "dashboard-net-sales-customer",
                "date": today,
                "payment_method": "Cash",
                "items": [{"product_id": product_id, "quantity": 2}],
                "discount": 10,
            },
        )
        assert invoice_response.status_code == 201, invoice_response.text
        invoice_id = invoice_response.json()["id"]

        after_dashboard = client.get("/dashboard").json()
        assert after_dashboard["today_sales"] == before_dashboard["today_sales"] + 190

        after_report = client.get("/reports/stock-sales", params={"date": today}).json()
        before_row = next(row for row in before_report["products"] if row["product_code"] == code)
        after_row = next(row for row in after_report["products"] if row["product_code"] == code)
        assert after_row["opening_stock"] == 20
        assert after_row["stock_received"] == 5
        assert after_row["sales_amount"] == before_row["sales_amount"] + 190
    finally:
        if invoice_id:
            client.delete(f"/invoices/{invoice_id}")
        if product_id:
            client.delete(f"/products/{product_id}")

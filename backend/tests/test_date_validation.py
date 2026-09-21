"""Date boundaries are enforced by invoice, report, and history APIs."""

from datetime import date, timedelta


def test_date_validation_rejects_manual_invoice_and_filter_dates(client):
    today = date.fromisoformat(client.get("/invoices/next-number").json()["date"])
    yesterday = (today - timedelta(days=1)).isoformat()
    tomorrow = (today + timedelta(days=1)).isoformat()

    previous_invoice = client.post(
        "/invoices",
        json={
            "customer_name": "date-validation-previous",
            "date": yesterday,
            "payment_method": "Cash",
            "items": [{"product_id": "missing", "quantity": 1}],
        },
    )
    assert previous_invoice.status_code == 400

    future_invoice = client.post(
        "/invoices",
        json={
            "customer_name": "date-validation-future",
            "date": tomorrow,
            "payment_method": "Cash",
            "items": [{"product_id": "missing", "quantity": 1}],
        },
    )
    assert future_invoice.status_code == 400

    future_report = client.get("/reports/stock-sales", params={"date": tomorrow})
    assert future_report.status_code == 400

    future_from = client.get("/invoices", params={"date_from": tomorrow})
    assert future_from.status_code == 422

    future_to = client.get("/invoices", params={"date_to": tomorrow})
    assert future_to.status_code == 422

    reversed_range = client.get("/invoices", params={"date_from": today.isoformat(), "date_to": yesterday})
    assert reversed_range.status_code == 422

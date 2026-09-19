"""Monthly stock and sales report based on stock transaction history and invoices."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from lib.db import db
from models.report import StockSalesReport

router = APIRouter(prefix="/reports")


def _month_bounds(month: str) -> tuple[str, str]:
    try:
        month_dt = datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format.") from exc
    start = month_dt.replace(day=1).strftime("%Y-%m-%d")
    if month_dt.month == 12:
        next_month = month_dt.replace(year=month_dt.year + 1, month=1, day=1).strftime("%Y-%m-%d")
    else:
        next_month = month_dt.replace(month=month_dt.month + 1, day=1).strftime("%Y-%m-%d")
    return start, next_month


@router.get("/stock-sales", response_model=StockSalesReport)
async def stock_sales_report(month: str = Query(..., description="Month in YYYY-MM format")):
    month_start_str, month_end_str = _month_bounds(month)

    products = await db.products.find({}).to_list(10000)
    rows: dict[str, dict] = {}
    for product in products:
        rows[product["id"]] = {
            "product_id": product["id"],
            "product_name": product["name"],
            "product_code": product["code"],
            "current_stock": int(product.get("stock", 0)),
            "stock_received": 0,
            "sold_quantity": 0,
            "sales_amount": 0.0,
        }

    transactions = await db.stock_transactions.find({}).to_list(20000)
    sold_references: set[tuple[str, str]] = set()
    for txn in transactions:
        product_id = txn.get("product_id")
        row = rows.get(product_id)
        if row is None:
            continue
        qty = int(txn.get("quantity", 0))
        created_at = txn.get("created_at")
        if created_at is None:
            continue
        created_date = created_at.date().isoformat() if hasattr(created_at, "date") else str(created_at)[:10]
        if month_start_str <= created_date < month_end_str:
            if txn.get("transaction_type") == "received":
                row["stock_received"] += qty
            elif txn.get("transaction_type") == "sold":
                row["sold_quantity"] += qty
                if txn.get("unit_price") is not None:
                    row["sales_amount"] += float(txn["unit_price"]) * qty
                reference_id = txn.get("reference_id")
                if reference_id:
                    sold_references.add((reference_id, product_id))

    invoice_docs = await db.invoices.find({}).to_list(20000)
    for invoice in invoice_docs:
        invoice_date = invoice.get("date")
        if not invoice_date:
            continue
        for item in invoice.get("items", []):
            product_id = item.get("product_id")
            row = rows.get(product_id)
            if row is None:
                continue
            if month_start_str <= invoice_date < month_end_str:
                if (invoice.get("id"), product_id) in sold_references:
                    continue
                row["sold_quantity"] += int(item.get("quantity", 0))
                row["sales_amount"] += float(item.get("total", 0) or 0)

    product_rows = []
    chart_rows = []
    total_received = 0
    total_sold_qty = 0
    total_sales_amount = 0.0
    products_sold = 0

    for row in sorted(rows.values(), key=lambda item: item["product_name"].lower()):
        stock_received = int(row["stock_received"])
        sold_quantity = int(row["sold_quantity"])
        opening_stock = row["current_stock"] + sold_quantity - stock_received
        closing_stock = opening_stock + stock_received - sold_quantity
        sales_amount = round(float(row["sales_amount"]), 2)

        total_received += stock_received
        total_sold_qty += sold_quantity
        total_sales_amount += sales_amount
        if sold_quantity > 0:
            products_sold += 1

        product_row = {
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "product_code": row["product_code"],
            "opening_stock": int(opening_stock),
            "stock_received": stock_received,
            "sold_quantity": sold_quantity,
            "closing_stock": int(closing_stock),
            "sales_amount": sales_amount,
        }
        product_rows.append(product_row)

        if stock_received > 0 or sold_quantity > 0:
            chart_rows.append(
                {
                    "product_name": row["product_name"],
                    "product_code": row["product_code"],
                    "stock_received": stock_received,
                    "sold_quantity": sold_quantity,
                    "sales_amount": sales_amount,
                }
            )

    note = None
    if not await db.stock_transactions.count_documents({}):
        note = "Historical stock-received transactions are not available for older inventory. The report uses invoice history for sales and current stock to estimate opening balances when no prior stock movement records exist."

    return {
        "selected_month": month,
        "summary": {
            "total_stock_received": int(total_received),
            "total_units_sold": int(total_sold_qty),
            "total_sales_amount": round(total_sales_amount, 2),
            "products_sold": int(products_sold),
        },
        "products": product_rows,
        "chart": chart_rows,
        "note": note,
    }

"""Daily and monthly stock and sales reports based on transactions and invoices."""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query

from lib.dates import today_iso
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


def _validate_date(date: str) -> str:
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format.") from exc
    if date > today_iso():
        raise HTTPException(status_code=400, detail="Report date cannot be in the future.")
    return date


def _transaction_date(value: object) -> str:
    if hasattr(value, "astimezone"):
        if getattr(value, "tzinfo", None) is None:
            value = value.replace(tzinfo=timezone.utc)
        zone = ZoneInfo(os.environ.get("APP_TZ", "Asia/Kolkata"))
        return value.astimezone(zone).date().isoformat()
    return str(value)[:10]


def _invoice_item_net_amount(invoice: dict, item: dict) -> float:
    item_total = float(item.get("total", 0) or 0)
    subtotal = float(invoice.get("subtotal", 0) or 0)
    discount = float(invoice.get("discount", 0) or 0)
    if subtotal <= 0 or discount <= 0:
        return item_total
    return max(0.0, item_total - discount * (item_total / subtotal))


async def _daily_stock_sales_report(selected_date: str) -> dict:
    products = await db.products.find({}).to_list(10000)
    rows: dict[str, dict] = {
        product["id"]: {
            "product_id": product["id"],
            "product_name": product["name"],
            "product_code": product["code"],
            "current_stock": int(product.get("stock", 0)),
            "received": 0,
            "initial_stock": 0,
            "sold": 0,
            "sales_amount": 0.0,
            "received_after": 0,
            "sold_after": 0,
            "all_sold": 0,
            "all_received": 0,
            "created_at": product.get("created_at"),
        }
        for product in products
    }

    transactions = await db.stock_transactions.find({}).to_list(20000)
    sold_references: set[tuple[str, str]] = set()
    for txn in transactions:
        product_id = txn.get("product_id")
        row = rows.get(product_id)
        created_at = txn.get("created_at")
        if row is None or created_at is None:
            continue
        movement_date = _transaction_date(created_at)
        quantity = int(txn.get("quantity", 0))
        transaction_type = txn.get("transaction_type")
        if transaction_type == "sold":
            row["all_sold"] += quantity
            reference_id = txn.get("reference_id")
            if reference_id:
                sold_references.add((reference_id, product_id))
            if movement_date == selected_date:
                row["sold"] += quantity
                row["sales_amount"] += float(txn.get("unit_price") or 0) * quantity
                row["sold_after"] += quantity
            elif movement_date >= selected_date:
                row["sold_after"] += quantity
        elif transaction_type == "received":
            row["all_received"] += quantity
            if txn.get("reference_id") == product_id:
                row["initial_stock"] += quantity
                if movement_date > selected_date:
                    row["received_after"] += quantity
            elif movement_date == selected_date:
                row["received"] += quantity
                row["received_after"] += quantity
            elif movement_date > selected_date:
                row["received_after"] += quantity

    invoices = await db.invoices.find({}).to_list(20000)
    for invoice in invoices:
        invoice_date = invoice.get("date")
        if not invoice_date:
            continue
        for item in invoice.get("items", []):
            product_id = item.get("product_id")
            row = rows.get(product_id)
            if row is None:
                continue
            quantity = int(item.get("quantity", 0))
            if invoice_date == selected_date and (invoice.get("id"), product_id) in sold_references:
                row["sales_amount"] -= float(invoice.get("discount", 0) or 0) * (
                    float(item.get("total", 0) or 0) / float(invoice.get("subtotal", 1) or 1)
                )
                continue
            if invoice_date == selected_date:
                row["sold"] += quantity
                row["sales_amount"] += _invoice_item_net_amount(invoice, item)
                row["sold_after"] += quantity
                row["all_sold"] += quantity
            elif invoice_date >= selected_date:
                row["sold_after"] += quantity
                row["all_sold"] += quantity

    received_product_ids = {txn.get("product_id") for txn in transactions if txn.get("transaction_type") == "received"}
    for row in rows.values():
        created_at = row.get("created_at")
        if row["product_id"] in received_product_ids or created_at is None:
            continue
        row["initial_stock"] = max(0, row["current_stock"] + row["all_sold"] - row["all_received"])

    product_rows = []
    chart_rows = []
    total_received = 0
    total_sold = 0
    total_sales_amount = 0.0
    products_sold = 0
    for row in sorted(rows.values(), key=lambda item: item["product_name"].lower()):
        opening_stock = row["current_stock"] - row["received_after"] + row["sold_after"]
        received = int(row["received"])
        sold = int(row["sold"])
        sales_amount = round(float(row["sales_amount"]), 2)
        closing_stock = opening_stock + received - sold
        total_received += received + int(row["initial_stock"])
        total_sold += sold
        total_sales_amount += sales_amount
        if sold > 0:
            products_sold += 1
        product_rows.append(
            {
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "product_code": row["product_code"],
                "opening_stock": int(opening_stock),
                "stock_received": received,
                "sold_quantity": sold,
                "closing_stock": int(closing_stock),
                "sales_amount": sales_amount,
            }
        )
        chart_received = received + int(row["initial_stock"])
        if chart_received > 0 or sold > 0:
            chart_rows.append(
                {
                    "product_name": row["product_name"],
                    "product_code": row["product_code"],
                    "stock_received": chart_received,
                    "sold_quantity": sold,
                    "sales_amount": sales_amount,
                }
            )

    return {
        "selected_month": selected_date,
        "selected_date": selected_date,
        "report_type": "daily",
        "summary": {
            "total_stock_received": total_received,
            "total_units_sold": total_sold,
            "total_sales_amount": round(total_sales_amount, 2),
            "products_sold": products_sold,
        },
        "products": product_rows,
        "chart": chart_rows,
        "note": None,
    }


@router.get("/stock-sales", response_model=StockSalesReport)
async def stock_sales_report(
    month: str | None = Query(default=None, description="Month in YYYY-MM format"),
    date: str | None = Query(default=None, description="Date in YYYY-MM-DD format"),
):
    if date:
        return await _daily_stock_sales_report(_validate_date(date))
    if not month:
        raise HTTPException(status_code=400, detail="Either month or date is required.")
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
            "initial_stock": 0,
            "sold_quantity": 0,
            "sales_amount": 0.0,
            "all_sold": 0,
            "all_received": 0,
            "created_at": product.get("created_at"),
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
        created_date = _transaction_date(created_at)
        if txn.get("transaction_type") == "received":
            row["all_received"] += qty
            if txn.get("reference_id") == product_id:
                row["initial_stock"] += qty
        elif txn.get("transaction_type") == "sold":
            row["all_sold"] += qty
        if month_start_str <= created_date < month_end_str:
            if txn.get("transaction_type") == "received":
                if txn.get("reference_id") != product_id:
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
                    row["sales_amount"] -= float(invoice.get("discount", 0) or 0) * (
                        float(item.get("total", 0) or 0) / float(invoice.get("subtotal", 1) or 1)
                    )
                    continue
                row["sold_quantity"] += int(item.get("quantity", 0))
                row["all_sold"] += int(item.get("quantity", 0))
                row["sales_amount"] += _invoice_item_net_amount(invoice, item)

    received_product_ids = {txn.get("product_id") for txn in transactions if txn.get("transaction_type") == "received"}
    for row in rows.values():
        created_at = row.get("created_at")
        if row["product_id"] in received_product_ids:
            continue
        row["initial_stock"] = max(0, row["current_stock"] + row["all_sold"] - row["all_received"])

    product_rows = []
    chart_rows = []
    total_received = 0
    total_sold_qty = 0
    total_sales_amount = 0.0
    products_sold = 0

    for row in sorted(rows.values(), key=lambda item: item["product_name"].lower()):
        stock_received = int(row["stock_received"])
        sold_quantity = int(row["sold_quantity"])
        opening_stock = int(row["initial_stock"])
        closing_stock = opening_stock + stock_received - sold_quantity
        sales_amount = round(float(row["sales_amount"]), 2)

        total_received += stock_received + int(row["initial_stock"])
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

        chart_received = stock_received + int(row["initial_stock"])
        if chart_received > 0 or sold_quantity > 0:
            chart_rows.append(
                {
                    "product_name": row["product_name"],
                    "product_code": row["product_code"],
                    "stock_received": chart_received,
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

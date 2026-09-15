"""Dashboard summary aggregates. "Today" is anchored server-side via lib.dates."""

from fastapi import APIRouter

from lib.dates import today_iso
from lib.db import db
from models.dashboard import DashboardSummary
from models.product import LOW_STOCK_THRESHOLD

router = APIRouter(prefix="/dashboard")


@router.get("", response_model=DashboardSummary)
async def dashboard_summary():
    today = today_iso()

    product_rows = await db.products.aggregate(
        [
            {
                "$group": {
                    "_id": None,
                    "total_products": {"$sum": 1},
                    "total_stock": {"$sum": "$stock"},
                    "low_stock": {
                        "$sum": {
                            "$cond": [
                                {"$and": [{"$gt": ["$stock", 0]}, {"$lte": ["$stock", LOW_STOCK_THRESHOLD]}]},
                                1,
                                0,
                            ]
                        }
                    },
                    "out_of_stock": {"$sum": {"$cond": [{"$lte": ["$stock", 0]}, 1, 0]}},
                }
            }
        ]
    ).to_list(1)
    products = product_rows[0] if product_rows else {}

    invoice_rows = await db.invoices.aggregate(
        [
            {"$match": {"date": today}},
            {"$group": {"_id": None, "count": {"$sum": 1}, "sales": {"$sum": "$total"}}},
        ]
    ).to_list(1)
    invoices = invoice_rows[0] if invoice_rows else {}

    return DashboardSummary(
        total_products=products.get("total_products", 0),
        total_stock=products.get("total_stock", 0),
        low_stock=products.get("low_stock", 0),
        out_of_stock=products.get("out_of_stock", 0),
        today_sales=round(invoices.get("sales", 0), 2),
        today_invoice_count=invoices.get("count", 0),
    )

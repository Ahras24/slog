"""Dashboard summary model."""

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_products: int = 0
    total_stock: int = 0
    low_stock: int = 0
    out_of_stock: int = 0
    today_sales: float = 0
    today_invoice_count: int = 0
    sale_count: int = 0

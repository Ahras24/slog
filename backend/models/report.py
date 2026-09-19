from pydantic import BaseModel, Field


class StockSalesSummary(BaseModel):
    total_stock_received: int = 0
    total_units_sold: int = 0
    total_sales_amount: float = 0
    products_sold: int = 0


class StockSalesProductRow(BaseModel):
    product_id: str
    product_name: str
    product_code: str
    opening_stock: int = 0
    stock_received: int = 0
    sold_quantity: int = 0
    closing_stock: int = 0
    sales_amount: float = 0


class StockSalesChartPoint(BaseModel):
    product_name: str
    product_code: str
    stock_received: int = 0
    sold_quantity: int = 0
    sales_amount: float = 0


class StockSalesReport(BaseModel):
    selected_month: str
    summary: StockSalesSummary = Field(default_factory=StockSalesSummary)
    products: list[StockSalesProductRow] = Field(default_factory=list)
    chart: list[StockSalesChartPoint] = Field(default_factory=list)
    note: str | None = None

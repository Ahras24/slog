"""Invoice models — snapshots preserve original details even if products change later."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from models.product import utcnow

PaymentMethod = Literal["Cash(S)", "Cash(A)", "Cash(I)", "Cash(Z)", "Cash"]
InvoiceStatus = Literal["Pending", "Finalized"]


class InvoiceItem(BaseModel):
    product_id: str
    product_name: str
    product_code: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    total: float = Field(ge=0)


class InvoiceCreateItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)
    unit_price: float | None = Field(default=None, ge=0)  # defaults to the product's current price


class InvoiceCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    company_name: str = ""
    street_address: str = ""
    city_pincode: str = ""
    phone: str = ""
    email: str = ""
    date: str | None = None  # YYYY-MM-DD; defaults to the server's today
    payment_method: PaymentMethod
    discount: float = Field(default=0, ge=0)
    gst_enabled: bool = False
    advance_amount: float = Field(default=0, ge=0)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=1)
    items: list[InvoiceCreateItem] = Field(min_length=1)


class InvoicePayment(BaseModel):
    id: str
    amount: float = Field(gt=0)
    payment_method: PaymentMethod
    paid_at: datetime


class InvoicePaymentCreate(BaseModel):
    id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    payment_method: PaymentMethod


class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_number: str
    date: str  # YYYY-MM-DD
    customer_name: str
    company_name: str = ""
    street_address: str = ""
    city_pincode: str = ""
    phone: str = ""
    email: str = ""
    payment_method: PaymentMethod | None = None
    items: list[InvoiceItem] = []
    subtotal: float = 0
    discount: float = 0
    gst_enabled: bool = False
    gst_amount: float = 0
    round_off: float = 0
    total: float = 0
    total_paid: float = 0
    remaining_balance: float = 0
    payments: list[InvoicePayment] = Field(default_factory=list)
    request_id: str | None = None
    stock_deducted: bool = True
    status: InvoiceStatus = "Finalized"
    finalized_at: datetime | None = None
    store_phone: str = ""  # snapshot of the store phone for the invoice footer
    created_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="before")
    @classmethod
    def populate_legacy_payment_fields(cls, values):
        if not isinstance(values, dict):
            return values
        values = values.copy()
        if "total_paid" not in values:
            values["total_paid"] = values.get("total", 0) if values.get("status", "Finalized") != "Pending" else 0
        if "remaining_balance" not in values:
            values["remaining_balance"] = max(0, values.get("total", 0) - values["total_paid"])
        return values


class NextInvoiceNumber(BaseModel):
    invoice_number: str
    date: str


class InvoiceListResponse(BaseModel):
    invoices: list[Invoice]
    page: int
    limit: int
    total: int
    total_pages: int

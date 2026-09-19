"""Invoice models — snapshots preserve original details even if products change later."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from models.product import utcnow

PaymentMethod = Literal["Cash(S)", "Cash(A)", "Cash(I)", "Cash(Z)", "Cash"]


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
    items: list[InvoiceCreateItem] = Field(min_length=1)


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
    round_off: float = 0
    total: float = 0
    status: str = "Finalized"
    store_phone: str = ""  # snapshot of the store phone for the invoice footer
    created_at: datetime = Field(default_factory=utcnow)


class NextInvoiceNumber(BaseModel):
    invoice_number: str
    date: str

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from models.product import utcnow


TransactionType = Literal["received", "sold"]


class StockTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: str
    product_code: str
    transaction_type: TransactionType
    quantity: int = Field(ge=1)
    unit_price: float | None = Field(default=None, ge=0)
    reference_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)

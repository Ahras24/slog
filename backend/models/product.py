"""Product models — the TS mirrors live in frontend/src/lib/types.ts."""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

LOW_STOCK_THRESHOLD = 10


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stock_status(stock: int) -> str:
    if stock <= 0:
        return "out_of_stock"
    if stock <= LOW_STOCK_THRESHOLD:
        return "low_stock"
    return "in_stock"


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    code: str
    stock: int = 0
    unit_price: float = 0.0
    status: str = "in_stock"  # derived from stock on read, never stored
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    stock: int = Field(default=0, ge=0)
    unit_price: float = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("must not be blank")
        return v


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    code: str | None = Field(default=None, min_length=1)
    stock: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("code")
    @classmethod
    def clean_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not v:
            raise ValueError("must not be blank")
        return v


class StockAddRequest(BaseModel):
    additional_quantity: int = Field(gt=0)  # adding stock can never be zero or negative

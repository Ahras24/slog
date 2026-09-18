"""Store settings — a single "store" document the settings page edits."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from models.product import utcnow

DEFAULT_INVOICE_PREFIX = "INV"
PREFIX_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class StoreSettings(BaseModel):
    store_name: str = "Wholesale Clothing Co."
    phone: str = ""
    email: str = ""
    street_address: str = ""
    city_pincode: str = ""
    invoice_prefix: str = DEFAULT_INVOICE_PREFIX
    updated_at: datetime = Field(default_factory=utcnow)


class StoreSettingsUpdate(BaseModel):
    store_name: str = Field(min_length=1)
    phone: str = ""
    email: str = ""
    street_address: str = ""
    city_pincode: str = ""
    invoice_prefix: str = DEFAULT_INVOICE_PREFIX

    @field_validator("store_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("invoice_prefix")
    @classmethod
    def clean_prefix(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if not v:
            return DEFAULT_INVOICE_PREFIX
        if len(v) > 10:
            raise ValueError("must be 10 characters or fewer")
        if not PREFIX_PATTERN.match(v):
            raise ValueError("use only letters, numbers, hyphen or underscore")
        return v

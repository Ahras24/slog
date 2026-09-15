"""Store settings — a single "store" document the settings page edits."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from models.product import utcnow


class StoreSettings(BaseModel):
    store_name: str = "Wholesale Clothing Co."
    phone: str = ""
    email: str = ""
    street_address: str = ""
    city_pincode: str = ""
    updated_at: datetime = Field(default_factory=utcnow)


class StoreSettingsUpdate(BaseModel):
    store_name: str = Field(min_length=1)
    phone: str = ""
    email: str = ""
    street_address: str = ""
    city_pincode: str = ""

    @field_validator("store_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

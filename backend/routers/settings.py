"""Store settings — read/upsert of the single "store" document."""

from datetime import datetime, timezone

from pymongo import ReturnDocument
from fastapi import APIRouter

from lib.db import db
from models.settings import StoreSettings, StoreSettingsUpdate

router = APIRouter(prefix="/settings")


@router.get("", response_model=StoreSettings)
async def get_settings():
    doc = await db.store_settings.find_one({"id": "store"})
    if not doc:
        doc = {"id": "store", **StoreSettings().model_dump()}
        await db.store_settings.insert_one(doc)
    doc.pop("_id", None)
    return StoreSettings(**doc)


@router.put("", response_model=StoreSettings)
async def update_settings(input: StoreSettingsUpdate):
    doc = await db.store_settings.find_one_and_update(
        {"id": "store"},
        {"$set": {**input.model_dump(), "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    doc.pop("_id", None)
    return StoreSettings(**doc)

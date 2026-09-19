"""Products & stock CRUD. All routes hang off this router (mounted under /api)."""

from pymongo import ReturnDocument
from fastapi import APIRouter, HTTPException

from lib.db import db
from models.product import (
    Product,
    ProductCreate,
    ProductUpdate,
    StockAddRequest,
    stock_status,
    utcnow,
)
from models.stock_transaction import StockTransaction

router = APIRouter(prefix="/products")


def _to_product(doc: dict) -> Product:
    doc.pop("_id", None)
    product = Product(**doc)
    product.status = stock_status(product.stock)
    return product


@router.get("", response_model=list[Product])
async def list_products():
    docs = await db.products.find().sort([("name", 1)]).to_list(5000)
    return [_to_product(doc) for doc in docs]


@router.post("", response_model=Product, status_code=201)
async def create_product(input: ProductCreate):
    if await db.products.find_one({"code": input.code}):
        raise HTTPException(status_code=409, detail="A product with this code already exists.")
    product = Product(name=input.name, code=input.code, stock=input.stock, unit_price=input.unit_price)
    await db.products.insert_one(product.model_dump())
    product.status = stock_status(product.stock)
    return product


@router.put("/{product_id}", response_model=Product)
async def update_product(product_id: str, input: ProductUpdate):
    updates = input.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    if "code" in updates:
        clash = await db.products.find_one({"code": updates["code"], "id": {"$ne": product_id}})
        if clash:
            raise HTTPException(status_code=409, detail="A product with this code already exists.")
    updates["updated_at"] = utcnow()
    doc = await db.products.find_one_and_update(
        {"id": product_id}, {"$set": updates}, return_document=ReturnDocument.AFTER
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found.")
    return _to_product(doc)


@router.patch("/{product_id}/stock", response_model=Product)
async def add_stock(product_id: str, input: StockAddRequest):
    doc = await db.products.find_one_and_update(
        {"id": product_id},
        {"$inc": {"stock": input.additional_quantity}, "$set": {"updated_at": utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found.")

    transaction = StockTransaction(
        product_id=doc["id"],
        product_name=doc["name"],
        product_code=doc["code"],
        transaction_type="received",
        quantity=input.additional_quantity,
        unit_price=float(doc.get("unit_price", 0.0)),
    )
    await db.stock_transactions.insert_one(transaction.model_dump())
    return _to_product(doc)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found.")
    return None

"""Invoice creation (with atomic stock deduction + sequential numbering) and history."""

import re
from datetime import datetime

from pymongo import ReturnDocument
from fastapi import APIRouter, HTTPException

from lib.dates import today_iso
from lib.db import db
from models.invoice import Invoice, InvoiceCreate, InvoiceItem, NextInvoiceNumber
from models.product import utcnow

router = APIRouter(prefix="/invoices")


def _clean(doc: dict) -> Invoice:
    doc.pop("_id", None)
    return Invoice(**doc)


def _number(seq: int) -> str:
    return f"INV-{seq:04d}"


@router.get("/next-number", response_model=NextInvoiceNumber)
async def next_invoice_number():
    """Preview only — the authoritative number is assigned atomically at finalize time."""
    counter = await db.counters.find_one({"_id": "invoice"})
    seq = (counter or {}).get("seq", 0) + 1
    return NextInvoiceNumber(invoice_number=_number(seq), date=today_iso())


@router.get("", response_model=list[Invoice])
async def list_invoices(search: str = "", date_from: str = "", date_to: str = ""):
    query: dict = {}
    term = search.strip()
    if term:
        rx = {"$regex": re.escape(term), "$options": "i"}
        query["$or"] = [
            {"invoice_number": rx},
            {"customer_name": rx},
            {"company_name": rx},
        ]
    date_range: dict = {}
    if date_from:
        date_range["$gte"] = date_from
    if date_to:
        date_range["$lte"] = date_to
    if date_range:
        query["date"] = date_range
    docs = await db.invoices.find(query).sort([("created_at", -1)]).to_list(2000)
    return [_clean(doc) for doc in docs]


@router.post("", response_model=Invoice, status_code=201)
async def create_invoice(input: InvoiceCreate):
    date = (input.date or "").strip() or today_iso()
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invoice date must be in YYYY-MM-DD format.")

    ids = [item.product_id for item in input.items]
    docs = await db.products.find({"id": {"$in": ids}}).to_list(len(ids) + 1)
    by_id = {doc["id"]: doc for doc in docs}
    for item in input.items:
        if item.product_id not in by_id:
            raise HTTPException(status_code=404, detail="One of the invoiced products no longer exists.")

    items: list[InvoiceItem] = []
    subtotal = 0.0
    for item in input.items:
        product = by_id[item.product_id]
        price = item.unit_price if item.unit_price is not None else float(product["unit_price"])
        line_total = round(item.quantity * price, 2)
        subtotal += line_total
        items.append(
            InvoiceItem(
                product_id=item.product_id,
                product_name=product["name"],
                product_code=product["code"],
                quantity=item.quantity,
                unit_price=price,
                total=line_total,
            )
        )
    subtotal = round(subtotal, 2)
    discount = round(input.discount, 2)
    if discount > subtotal:
        raise HTTPException(status_code=400, detail="Discount cannot exceed the subtotal.")
    total_raw = round(subtotal - discount, 2)
    grand_total = round(total_raw)
    round_off = round(grand_total - total_raw, 2)

    # Atomic, all-or-nothing stock deduction: each decrement is guarded on stock >= qty.
    deducted: list[tuple[str, int]] = []
    for item in items:
        updated = await db.products.find_one_and_update(
            {"id": item.product_id, "stock": {"$gte": item.quantity}},
            {"$inc": {"stock": -item.quantity}, "$set": {"updated_at": utcnow()}},
        )
        if updated is None:
            for product_id, quantity in deducted:  # roll back what was already taken
                await db.products.update_one({"id": product_id}, {"$inc": {"stock": quantity}})
            product = by_id[item.product_id]
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock available for {product['name']}.",
            )
        deducted.append((item.product_id, item.quantity))

    counter = await db.counters.find_one_and_update(
        {"_id": "invoice"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    settings = await db.store_settings.find_one({"id": "store"}) or {}

    invoice = Invoice(
        invoice_number=_number(counter["seq"]),
        date=date,
        customer_name=input.customer_name.strip(),
        company_name=input.company_name.strip(),
        street_address=input.street_address.strip(),
        city_pincode=input.city_pincode.strip(),
        phone=input.phone.strip(),
        email=input.email.strip(),
        items=items,
        subtotal=subtotal,
        discount=discount,
        round_off=round_off,
        total=float(grand_total),
        store_phone=(settings.get("phone") or ""),
    )
    await db.invoices.insert_one(invoice.model_dump())
    return invoice


@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    doc = await db.invoices.find_one({"id": invoice_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return _clean(doc)

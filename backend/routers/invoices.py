"""Invoice creation (with atomic stock deduction + sequential numbering) and history."""

import re
from datetime import datetime

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, HTTPException

from lib.dates import today_iso
from lib.db import db
from models.invoice import Invoice, InvoiceCreate, InvoiceItem, InvoiceListResponse, NextInvoiceNumber
from models.product import utcnow
from models.settings import DEFAULT_INVOICE_PREFIX
from models.stock_transaction import StockTransaction

router = APIRouter(prefix="/invoices")


def _clean(doc: dict) -> Invoice:
    doc.pop("_id", None)
    return Invoice(**doc)


def _number(seq: int, prefix: str = DEFAULT_INVOICE_PREFIX) -> str:
    return f"{prefix}-{seq:04d}"


async def _invoice_prefix() -> str:
    """Store-configured invoice prefix; the sequence itself stays automatic."""
    doc = await db.store_settings.find_one({"id": "store"}) or {}
    return (doc.get("invoice_prefix") or DEFAULT_INVOICE_PREFIX).strip() or DEFAULT_INVOICE_PREFIX


def _parse_seq(invoice_number: str) -> int:
    """"INV-0007" / "WCC-0007" -> 7. Prefix-agnostic; unparseable numbers count as 0."""
    match = re.search(r"(\d+)\s*$", invoice_number or "")
    return int(match.group(1)) if match else 0


async def _highest_existing_seq() -> int:
    """Highest sequence among invoices that actually exist right now.

    Parsed in Python rather than relying on a lexicographic sort, which would rank
    "INV-10000" below "INV-9999" once the sequence outgrows four digits.
    """
    numbers = await db.invoices.find({}, {"invoice_number": 1, "_id": 0}).to_list(20000)
    return max((_parse_seq(doc.get("invoice_number", "")) for doc in numbers), default=0)


async def _reserve_invoice_number(prefix: str) -> str:
    """Assign the next number, reconciled against the invoices actually stored.

    The counter alone goes stale whenever invoices are deleted (numbering would keep
    climbing past an empty history), so it is realigned to the real maximum first —
    downwards after deletions, upwards if it ever lagged behind. The sequence is shared
    across prefixes: changing the prefix renames future numbers, it does not restart them.
    """
    highest = await _highest_existing_seq()
    counter = await db.counters.find_one({"_id": "invoice"})
    if (counter or {}).get("seq", 0) != highest:
        await db.counters.update_one({"_id": "invoice"}, {"$set": {"seq": highest}}, upsert=True)
    updated = await db.counters.find_one_and_update(
        {"_id": "invoice"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _number(updated["seq"], prefix)


@router.get("/next-number", response_model=NextInvoiceNumber)
async def next_invoice_number():
    """Preview only — the authoritative number is assigned atomically at finalize time."""
    prefix = await _invoice_prefix()
    return NextInvoiceNumber(
        invoice_number=_number(await _highest_existing_seq() + 1, prefix),
        date=today_iso(),
    )


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(search: str = "", date_from: str = "", date_to: str = "", page: int = 1, limit: int = 10):
    if page < 1:
        raise HTTPException(status_code=422, detail="Page must be at least 1.")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="Limit must be between 1 and 100.")
    today = today_iso()
    for label, value in (("From", date_from), ("To", date_to)):
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"{label} date must be in YYYY-MM-DD format.") from exc
            if value > today:
                raise HTTPException(status_code=422, detail=f"{label} date cannot be in the future.")
    if date_from and date_to and date_to < date_from:
        raise HTTPException(status_code=422, detail="To date cannot be earlier than From date.")

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
    total = await db.invoices.count_documents(query)
    total_pages = (total + limit - 1) // limit
    docs = (
        await db.invoices.find(query)
        .sort([("created_at", -1), ("invoice_number", -1)])
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )
    return InvoiceListResponse(
        invoices=[_clean(doc) for doc in docs],
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
    )


@router.post("", response_model=Invoice, status_code=201)
async def create_invoice(input: InvoiceCreate):
    date = today_iso()
    submitted_date = (input.date or "").strip()
    if submitted_date and submitted_date != date:
        raise HTTPException(status_code=400, detail="New invoices must use today's date.")

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

    settings = await db.store_settings.find_one({"id": "store"}) or {}
    prefix = (settings.get("invoice_prefix") or DEFAULT_INVOICE_PREFIX).strip() or DEFAULT_INVOICE_PREFIX

    # The unique index on invoice_number is the final arbiter: on the rare race where two
    # finalizations reserve the same number, retry with a freshly reconciled one.
    last_error: Exception | None = None
    for _ in range(5):
        invoice = Invoice(
            invoice_number=await _reserve_invoice_number(prefix),
            date=date,
            customer_name=input.customer_name.strip(),
            company_name=input.company_name.strip(),
            street_address=input.street_address.strip(),
            city_pincode=input.city_pincode.strip(),
            phone=input.phone.strip(),
            email=input.email.strip(),
            payment_method=input.payment_method,
            items=items,
            subtotal=subtotal,
            discount=discount,
            round_off=round_off,
            total=float(grand_total),
            store_phone=(settings.get("phone") or ""),
        )
        try:
            await db.invoices.insert_one(invoice.model_dump())
            for item in invoice.items:
                existing = await db.stock_transactions.find_one(
                    {"reference_id": invoice.id, "product_id": item.product_id, "transaction_type": "sold"}
                )
                if existing:
                    continue
                transaction = StockTransaction(
                    product_id=item.product_id,
                    product_name=item.product_name,
                    product_code=item.product_code,
                    transaction_type="sold",
                    quantity=item.quantity,
                    unit_price=float(item.unit_price),
                    reference_id=invoice.id,
                )
                await db.stock_transactions.insert_one(transaction.model_dump())
            return invoice
        except DuplicateKeyError as exc:
            last_error = exc

    for product_id, quantity in deducted:  # numbering exhausted its retries: give the stock back
        await db.products.update_one({"id": product_id}, {"$inc": {"stock": quantity}})
    raise HTTPException(status_code=409, detail="Could not assign a unique invoice number. Please try again.") from last_error


@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    doc = await db.invoices.find_one({"id": invoice_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return _clean(doc)


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(invoice_id: str):
    """Remove an invoice record. Stock is deliberately left as-is — deleting the record
    does not un-sell the goods; use Add Stock if the items came back."""
    result = await db.invoices.delete_one({"id": invoice_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return None

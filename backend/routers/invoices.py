"""Invoice creation (with atomic stock deduction + sequential numbering) and history."""

import re
from datetime import datetime

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, HTTPException

from lib.dates import today_iso
from lib.db import db
from models.invoice import (
    Invoice,
    InvoiceCreate,
    InvoiceItem,
    InvoiceListResponse,
    InvoicePayment,
    InvoicePaymentCreate,
    NextInvoiceNumber,
)
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


async def _reconcile_invoice_counter() -> int:
    highest = await _highest_existing_seq()
    counter = await db.counters.find_one({"_id": "invoice"})
    if (counter or {}).get("seq", 0) != highest:
        await db.counters.update_one({"_id": "invoice"}, {"$set": {"seq": highest}}, upsert=True)
    return highest


async def _reserve_invoice_number(prefix: str) -> str:
    """Reserve the next number from the highest sequence among stored invoices.

    The sequence is shared across prefixes: changing the prefix renames future numbers,
    it does not restart them.
    """
    await _reconcile_invoice_counter()
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
async def list_invoices(
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "all",
    page: int = 1,
    limit: int = 10,
):
    if page < 1:
        raise HTTPException(status_code=422, detail="Page must be at least 1.")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="Limit must be between 1 and 100.")
    normalized_status = status.strip().lower()
    if normalized_status not in {"all", "pending", "finalized"}:
        raise HTTPException(status_code=422, detail="Status must be all, pending, or finalized.")
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
    if normalized_status == "pending":
        query["status"] = {"$in": ["Pending", "pending"]}
    elif normalized_status == "finalized":
        query["$and"] = [
            {
                "$or": [
                    {"status": {"$in": ["Finalized", "finalized"]}},
                    {"status": {"$exists": False}},
                ]
            }
        ]
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
    existing_request = await db.invoices.find_one({"request_id": input.request_id})
    if existing_request:
        return _clean(existing_request)

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
    discounted_subtotal = round(subtotal - discount, 2)
    gst_amount = round(discounted_subtotal * 0.05, 2) if input.gst_enabled else 0.0
    total_raw = round(discounted_subtotal + gst_amount, 2)
    grand_total = round(total_raw)
    round_off = round(grand_total - total_raw, 2)
    advance_amount = round(input.advance_amount, 2)
    if advance_amount > grand_total:
        raise HTTPException(status_code=400, detail="Advance amount cannot exceed the invoice total.")
    total_paid = advance_amount
    remaining_balance = round(grand_total - total_paid, 2)
    status = "Finalized" if remaining_balance == 0 else "Pending"
    now = utcnow()
    payments = (
        [
            InvoicePayment(
                id=f"{input.request_id}:initial",
                amount=advance_amount,
                payment_method=input.payment_method,
                paid_at=now,
            )
        ]
        if advance_amount > 0
        else []
    )

    # Atomic, all-or-nothing stock deduction: each decrement is guarded on stock >= qty.
    deducted: list[tuple[str, int]] = []
    quantities: dict[str, int] = {}
    for item in items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    for product_id, quantity in quantities.items():
        updated = await db.products.find_one_and_update(
            {
                "id": product_id,
                "stock": {"$gte": quantity},
                "_deducted_invoice_request_ids": {"$ne": input.request_id},
            },
            {
                "$inc": {"stock": -quantity},
                "$addToSet": {"_deducted_invoice_request_ids": input.request_id},
                "$set": {"updated_at": utcnow()},
            },
        )
        if updated is None:
            already_deducted = await db.products.find_one(
                {"id": product_id, "_deducted_invoice_request_ids": input.request_id},
                {"_id": 1},
            )
            if already_deducted:
                continue
            for product_id, quantity in deducted:
                await db.products.update_one(
                    {"id": product_id},
                    {
                        "$inc": {"stock": quantity},
                        "$pull": {"_deducted_invoice_request_ids": input.request_id},
                    },
                )
            product = by_id[product_id]
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock available for {product['name']}.",
            )
        deducted.append((product_id, quantity))

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
            gst_enabled=input.gst_enabled,
            gst_amount=gst_amount,
            round_off=round_off,
            total=float(grand_total),
            total_paid=total_paid,
            remaining_balance=remaining_balance,
            payments=payments,
            request_id=input.request_id,
            stock_deducted=True,
            status=status,
            finalized_at=now if status == "Finalized" else None,
            store_phone=(settings.get("phone") or ""),
        )
        try:
            await db.invoices.insert_one(invoice.model_dump())
            for product_id, quantity in quantities.items():
                existing = await db.stock_transactions.find_one(
                    {"reference_id": invoice.id, "product_id": product_id, "transaction_type": "sold"}
                )
                if existing:
                    continue
                product_items = [item for item in invoice.items if item.product_id == product_id]
                product = product_items[0]
                transaction = StockTransaction(
                    product_id=product_id,
                    product_name=product.product_name,
                    product_code=product.product_code,
                    transaction_type="sold",
                    quantity=quantity,
                    unit_price=sum(item.total for item in product_items) / quantity,
                    reference_id=invoice.id,
                )
                await db.stock_transactions.insert_one(transaction.model_dump())
            return invoice
        except DuplicateKeyError as exc:
            last_error = exc
            existing_request = await db.invoices.find_one({"request_id": input.request_id})
            if existing_request:
                for product_id, quantity in deducted:
                    await db.products.update_one(
                        {"id": product_id},
                        {
                            "$inc": {"stock": quantity},
                            "$pull": {"_deducted_invoice_request_ids": input.request_id},
                        },
                    )
                return _clean(existing_request)

    for product_id, quantity in deducted:
        await db.products.update_one(
            {"id": product_id},
            {
                "$inc": {"stock": quantity},
                "$pull": {"_deducted_invoice_request_ids": input.request_id},
            },
        )
    raise HTTPException(status_code=409, detail="Could not assign a unique invoice number. Please try again.") from last_error


@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    doc = await db.invoices.find_one({"id": invoice_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return _clean(doc)


@router.post("/{invoice_id}/payments", response_model=Invoice)
async def add_invoice_payment(invoice_id: str, payment: InvoicePaymentCreate):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    existing_payment = next(
        (saved for saved in invoice.get("payments", []) if saved.get("id") == payment.id),
        None,
    )
    if existing_payment:
        return _clean(invoice)
    if invoice.get("status", "Finalized").lower() != "pending":
        raise HTTPException(status_code=409, detail="Only pending invoices can receive payments.")

    amount = round(payment.amount, 2)
    total = round(float(invoice.get("total", 0)), 2)
    total_paid = round(float(invoice.get("total_paid", 0)), 2)
    remaining = round(float(invoice.get("remaining_balance", total - total_paid)), 2)
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Payment amount must be greater than zero.")
    if amount > remaining:
        raise HTTPException(status_code=400, detail="Payment cannot exceed the remaining balance.")

    now = utcnow()
    paid_expression = {
        "$round": [{"$add": [{"$ifNull": ["$total_paid", 0]}, amount]}, 2]
    }
    remaining_expression = {
        "$round": [{"$subtract": [{"$ifNull": ["$remaining_balance", total]}, amount]}, 2]
    }
    updated = await db.invoices.find_one_and_update(
        {
            "id": invoice_id,
            "status": {"$in": ["Pending", "pending"]},
            "remaining_balance": {"$gte": amount},
            "payments.id": {"$ne": payment.id},
        },
        [
            {
                "$set": {
                    "payments": {
                        "$concatArrays": [
                            {"$ifNull": ["$payments", []]},
                            [
                                InvoicePayment(
                                    id=payment.id,
                                    amount=amount,
                                    payment_method=payment.payment_method,
                                    paid_at=now,
                                ).model_dump()
                            ],
                        ]
                    },
                    "total_paid": paid_expression,
                    "remaining_balance": remaining_expression,
                    "status": {
                        "$cond": [{"$eq": [remaining_expression, 0]}, "Finalized", "Pending"]
                    },
                    "finalized_at": {
                        "$cond": [
                            {"$eq": [remaining_expression, 0]},
                            now,
                            {"$ifNull": ["$finalized_at", None]},
                        ]
                    },
                }
            }
        ],
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        current = await db.invoices.find_one({"id": invoice_id})
        if current and any(saved.get("id") == payment.id for saved in current.get("payments", [])):
            return _clean(current)
        if current is None:
            raise HTTPException(status_code=404, detail="Invoice not found.")
        if current.get("status", "Finalized").lower() != "pending":
            raise HTTPException(status_code=409, detail="Only pending invoices can receive payments.")
        raise HTTPException(status_code=400, detail="Payment exceeds the remaining balance.")
    return _clean(updated)


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(invoice_id: str):
    """Restore sold stock and remove all invoice-backed sales records."""
    invoice = await db.invoices.find_one({"id": invoice_id})
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    quantities: dict[str, int] = {}
    for item in invoice.get("items", []):
        product_id = item.get("product_id")
        quantity = int(item.get("quantity", 0))
        if product_id and quantity > 0:
            quantities[product_id] = quantities.get(product_id, 0) + quantity

    for product_id, quantity in quantities.items():
        # The stock update and marker are one atomic document update. Retaining the
        # marker makes retries/concurrent delete requests safe on standalone MongoDB.
        await db.products.update_one(
            {"id": product_id, "_restored_invoice_ids": {"$ne": invoice_id}},
            {
                "$inc": {"stock": quantity},
                "$addToSet": {"_restored_invoice_ids": invoice_id},
                "$pull": {"_deducted_invoice_request_ids": invoice.get("request_id")},
                "$set": {"updated_at": utcnow()},
            },
        )

    await db.stock_transactions.delete_many(
        {"reference_id": invoice_id, "transaction_type": "sold"}
    )
    result = await db.invoices.delete_one({"id": invoice_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    await _reconcile_invoice_counter()
    return None

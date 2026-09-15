"""Idempotent demo seed. Run once: cd /app/backend && python seed.py"""

import asyncio
from datetime import datetime, timedelta, timezone

from lib.db import client, db, ensure_indexes
from models.invoice import Invoice, InvoiceItem
from models.product import Product

STORE_SETTINGS = {
    "id": "store",
    "store_name": "Wholesale Clothing Co.",
    "phone": "+91 97313 66545",
    "email": "orders@wholesaleclothingco.in",
    "street_address": "48/2 Commercial Street, Textile Market",
    "city_pincode": "Bengaluru, Karnataka - 560001",
}

PRODUCTS = [
    ("Premium Cotton Oxford Shirt (Men)", "SHIRT-OXF-01", 140, 650),
    ("Linen Casual Slim-Fit Trousers", "TRS-LIN-04", 48, 820),
    ("Pure Mulmul Handblock Kurti", "KRT-MUL-12", 8, 540),
    ("Heavyweight French Terry Hoodie", "HD-FT-08", 25, 1150),
    ("Denim Relaxed Fit Jeans (Indigo)", "DNM-RLX-02", 4, 980),
    ("Chanderi Silk Embroidered Dupatta", "DPT-CHD-09", 0, 420),
    ("Organic Cotton Crewneck T-Shirt (Pack of 3)", "TSH-ORG-03", 95, 790),
    ("Silk Blend Formal Blazer", "BLZ-SLK-15", 0, 2850),
]

INVOICES = [
    {
        "number": "INV-0001",
        "days_ago": 1,
        "customer": (
            "Rajesh Kumar",
            "Metro Retailers Hub",
            "Shop #14, Fashion Avenue",
            "Hyderabad, Telangana - 500001",
            "+91 98450 12345",
            "metro.orders@gmail.com",
        ),
        "items": [("SHIRT-OXF-01", 20), ("TRS-LIN-04", 10)],
        "discount": 500,
    },
    {
        "number": "INV-0002",
        "days_ago": 0,
        "customer": (
            "Ananya Sharma",
            "Elegance Boutique",
            "22 Brigade Road",
            "Bengaluru, Karnataka - 560025",
            "+91 99801 88776",
            "ananya@eleganceboutique.com",
        ),
        "items": [("TSH-ORG-03", 15), ("HD-FT-08", 10)],
        "discount": 850,
    },
]


async def main() -> None:
    await ensure_indexes()

    if await db.store_settings.count_documents({}) == 0:
        await db.store_settings.insert_one(STORE_SETTINGS.copy())
        print("seeded store settings")

    if await db.products.count_documents({}) == 0:
        for name, code, stock, price in PRODUCTS:
            product = Product(name=name, code=code, stock=stock, unit_price=float(price))
            await db.products.insert_one(product.model_dump())
        print(f"seeded {len(PRODUCTS)} products")

    if await db.invoices.count_documents({}) == 0:
        catalog = {doc["code"]: doc async for doc in db.products.find({})}
        seq = 0
        for spec in INVOICES:
            seq += 1
            date = (datetime.now(timezone.utc) - timedelta(days=spec["days_ago"])).strftime("%Y-%m-%d")
            name, company, street, city, phone, email = spec["customer"]
            items: list[InvoiceItem] = []
            subtotal = 0.0
            for code, qty in spec["items"]:
                product = catalog[code]
                price = float(product["unit_price"])
                line_total = round(qty * price, 2)
                subtotal += line_total
                items.append(
                    InvoiceItem(
                        product_id=product["id"],
                        product_name=product["name"],
                        product_code=product["code"],
                        quantity=qty,
                        unit_price=price,
                        total=line_total,
                    )
                )
            subtotal = round(subtotal, 2)
            discount = float(spec["discount"])
            total_raw = round(subtotal - discount, 2)
            grand_total = round(total_raw)
            invoice = Invoice(
                invoice_number=spec["number"],
                date=date,
                customer_name=name,
                company_name=company,
                street_address=street,
                city_pincode=city,
                phone=phone,
                email=email,
                items=items,
                subtotal=subtotal,
                discount=discount,
                round_off=round(grand_total - total_raw, 2),
                total=float(grand_total),
                store_phone=STORE_SETTINGS["phone"],
            )
            await db.invoices.insert_one(invoice.model_dump())
        await db.counters.update_one({"_id": "invoice"}, {"$set": {"seq": seq}}, upsert=True)
        print(f"seeded {seq} invoices")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())

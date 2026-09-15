# Spec — Wholesale Clothing Admin Panel (Stock Management & Billing)

Internal admin dashboard (no customer-facing features, no cart, no payments, no login — opens straight to the dashboard).

## Stack & entry points
- Backend: FastAPI + motor (Mongo `app` db), port 8001, all routes on `api_router` under `/api`.
- Frontend: Vite + React 19 + TS strict + Tailwind v4 + shadcn (base-ui), port 3000, relative `/api` calls via `src/lib/api.ts`, TanStack Query.
- Design: light theme, navy accent `#0F2942`, Plus Jakarta Sans (app), Poppins + Lora (invoice sheet), left sidebar, `w-64`, seed store: "Wholesale Clothing Co." phone "+91 97313 66545".

## Data model (Pydantic ↔ TS mirrors in `frontend/src/lib/types.ts`)
- **Product** (`products`): `id` (uuid4 str), `name`, `code` (unique, uppercased), `stock` (int ≥ 0), `unit_price` (float ≥ 0), `status` (DERIVED on read, never stored: 0 → `out_of_stock`, 1–10 → `low_stock`, >10 → `in_stock`), `created_at`, `updated_at`.
- **Invoice** (`invoices`): `id`, `invoice_number` (unique, `INV-0001` style, assigned server-side at finalize from `counters` collection, seq atomic `$inc`), `date` (YYYY-MM-DD str), customer snapshot (`customer_name` required, `company_name`, `street_address`, `city_pincode`, `phone`, `email`), `items[]` snapshot (`product_id`, `product_name`, `product_code`, `quantity`, `unit_price`, `total`), `subtotal`, `discount`, `round_off` (only shown non-zero; grand total = round(subtotal − discount)), `total`, `status: "Finalized"`, `store_phone` (snapshot for invoice footer), `created_at`.
- **StoreSettings** (`store_settings`, single doc `id: "store"`): `store_name`, `phone`, `email`, `street_address`, `city_pincode`.

## API (all under `/api`)
- `GET /products` (sorted by name), `POST /products` (409 on duplicate code), `PUT /products/{id}` (409 dup code excluding self; direct stock edit allowed, ≥0), `PATCH /products/{id}/stock` (body `{additional_quantity}` > 0), `DELETE /products/{id}` (204).
- `GET /invoices/next-number` (preview `{invoice_number, date}` — authoritative number assigned at finalize), `GET /invoices?search=&date_from=&date_to=` (search matches invoice_number/customer_name/company_name), `POST /invoices` (atomic all-or-nothing stock deduction guarded on `stock >= qty`, rollback on any failure → 409 "Insufficient stock available for X."; discount > subtotal → 400; invalid date → 400), `GET /invoices/{id}`.
- `GET /dashboard` — `total_products`, `total_stock`, `low_stock`, `out_of_stock`, `today_sales`, `today_invoice_count` ("today" anchored server-side via `lib.dates.today_iso()` UTC).
- `GET/PUT /settings`.
- Template endpoints `GET /` and `POST/GET /status` also exist (connectivity probe pattern).

## Key flows
1. Dashboard (/): 6 summary cards + reusable StockTable (search by name/code, filter tabs All/In Stock/Low Stock/Out of Stock, actions Edit / Add Stock / Sell). Sell → `/invoices/new?product={id}` preselects the product.
2. Products (/products): same StockTable + Add Product modal (shared add/edit `ProductFormModal`, delete confirm inside edit modal).
3. Create Invoice (/invoices/new): Issued To form (name required), auto number (preview, assigned at finalize), date defaults to server today, item rows via searchable ProductPicker (auto code/price), qty validated against stock minus same product already in other rows → inline warning "Insufficient stock available. Only N left in stock." Finalize → confirm dialog → POST → snapshot modal with Print.
4. Invoice History (/invoices): search + date range (server-side), rows View/Print. View opens snapshot modal ("exactly as created" — items are snapshots, immune to later product edits/deletes). Print → PrintPortal → `window.print()`.
5. Settings (/settings): store details; only affect NEW invoices.
6. Printing: `#invoice-print-root` portal; `@media print` hides `#root`, prints A4 portrait, beige chips/headers force color-adjust exact.

## Seed (`backend/seed.py`, idempotent, already applied)
8 clothing products (Kurti stock 8 low, Jeans stock 4 low, Dupatta + Blazer stock 0 out), 2 invoices: INV-0001 yesterday (Rajesh Kumar/Metro Retailers Hub, ₹20,700), INV-0002 today (Ananya Sharma/Elegance Boutique, ₹22,500), counter seq=2 → next number INV-0003.

## Credentials
No login/auth anywhere — the panel is open. `memory/test_credentials.md` notes this too.

## Notes for testers
- Do NOT click "Print Invoice" buttons in headless runs — they call `window.print()` (native dialog).
- Money formatting: `Intl.NumberFormat("en-IN", {currency: "INR"})` → "₹1,234.00".

# Spec — Wholesale Clothing Admin Panel (Stock Management & Billing)

Internal admin dashboard (no customer-facing features, no cart, no payments, no login — opens straight to the dashboard).

## Stack & entry points
- Backend: FastAPI + motor (Mongo `app` db), port 8001, all routes on `api_router` under `/api`.
- Frontend: Vite + React 19 + TS strict + Tailwind v4 + shadcn (base-ui), port 3000, relative `/api` calls via `src/lib/api.ts`, TanStack Query.
- Design: light theme, navy accent `#0F2942`, Plus Jakarta Sans (app), Poppins + Lora (invoice sheet), left sidebar `w-64`, seed store: "Wholesale Clothing Co." phone "+91 97313 66545".

## Pages & navigation (current — v3 layout)
- Desktop: left sidebar nav — Dashboard (/), Products & Stock (/products), Invoice History (/invoices), Settings (/settings). **Mobile: fixed bottom navigation bar** (hamburger/Sheet removed; bottom items use testids `bottom-nav-*`). **No Create Invoice nav item and no /invoices/new route** — invoice creation is the `InvoiceBuilderModal`.
- StockTable: **SI No column** + **client-side pagination, 10 products per page** (testids `stock-pagination-prev/next/info/range`); search/filter changes reset to page 1.
- InvoiceBuilderModal item rows: Product 4/12, Code 2/12, **Qty 2/12 (input text-center px-2 so the count is visible)**, Unit Price 2/12, Total + remove (X inside the row card, `shrink-0`); row testid `invoice-item-row-{i}`.
- **Dashboard (/)**: 6 large summary cards ONLY (products section removed in v2). "Create Invoice" button opens InvoiceBuilderModal. Wildcard redirects to /.
- **Products & Stock (/products)**: StockTable (px-4 column padding) + Add Product / Edit / Add Stock modals; "Sell" action opens InvoiceBuilderModal with the product preselected.
- **Invoice History (/invoices)**: search + date range, View/Print actions; header + empty-state "Create Invoice" buttons open InvoiceBuilderModal.
- **Settings (/settings)**: store details; only affect NEW invoices.

## Data model (Pydantic ↔ TS mirrors in `frontend/src/lib/types.ts`)
- **Product** (`products`): `id` (uuid4 str), `name`, `code` (unique, uppercased), `stock` (int ≥ 0), `unit_price` (float ≥ 0), `status` (DERIVED on read: 0 → `out_of_stock`, 1–10 → `low_stock`, >10 → `in_stock`), `created_at`, `updated_at`.
- **Invoice** (`invoices`): `id`, `invoice_number` (unique, `INV-0001` style, assigned server-side at finalize from `counters` seq `$inc`), `date` (YYYY-MM-DD str), customer snapshot (`customer_name` required + company/street/city/phone/email), `items[]` snapshot (`product_id`, `product_name`, `product_code`, `quantity`, `unit_price`, `total`), `subtotal`, `discount`, `round_off` (shown only non-zero; total = round(subtotal − discount)), `total`, `status: "Finalized"`, `store_phone` snapshot, `created_at`.
- **StoreSettings** (`store_settings`, doc `id: "store"`): `store_name`, `phone`, `email`, `street_address`, `city_pincode`.

## API (all under `/api`)
- `GET /products`, `POST /products` (409 duplicate code), `PUT /products/{id}` (409 excluding self), `PATCH /products/{id}/stock` (`{additional_quantity}` > 0), `DELETE /products/{id}` (204).
- `GET /invoices/next-number` (preview; authoritative number assigned at finalize), `GET /invoices?search=&date_from=&date_to=`, `POST /invoices` (atomic all-or-nothing stock deduction guarded `stock >= qty`, rollback on failure → 409 "Insufficient stock available for X."; discount > subtotal → 400; bad date → 400), `GET /invoices/{id}`.
- **Invoice numbering is self-healing** (`_reserve_invoice_number()` in `routers/invoices.py`): before each `$inc` the `counters.invoice` doc is realigned to `_highest_existing_seq()` — the max sequence parsed from invoices that actually exist. So deleting invoices straight from the DB makes numbering fall back (empty history → next is INV-0001) instead of climbing forever off a stale counter. Sequences are parsed in Python, not sorted lexicographically, so >9999 still orders correctly; insert is wrapped in a 5-attempt `DuplicateKeyError` retry against the unique `invoice_number` index, and stock is rolled back if every attempt fails.
- `GET /dashboard` — `total_products`, `total_stock`, `low_stock`, `out_of_stock`, `today_sales`, `today_invoice_count` (server-side "today" via `lib.dates.today_iso()` UTC).
- `GET/PUT /settings`. Template probe endpoints `GET /`, `POST/GET /status` remain.

## Invoice creation flow (v2)
InvoiceBuilderModal (`components/invoices/InvoiceBuilderModal.tsx`): opened from Dashboard button / Products Sell / History buttons. Fresh form each open (`preselectProductId` preselects Sell product). Issued To (name required), auto number (preview; assigned at finalize), date = server today, item rows via searchable ProductPicker (auto code/price), qty validated against stock minus same product in other rows → inline "Insufficient stock available. Only N left in stock." Finalize → ConfirmDialog → POST → snapshot InvoiceViewModal opens over the builder with Print.

## Invoice viewing & printing (v2 fixes)
- InvoiceViewModal preview renders the sheet at TRUE A4 width (`w-[210mm] p-[18mm]`, modal `max-w-4xl`) — 1:1 with the printout.
- Print: PrintPortal mounts `#invoice-print-root` to body; print CSS hides `body > *:not(#invoice-print-root)` (covers BOTH the app root and base-ui dialog portals — fixes the double-invoice/different-sizes print bug), `@page` A4 portrait margin 0, color-adjust exact.
- History snapshots are immutable — immune to later product edits/deletes.

## Seed / current data state
12 clothing products (3 low stock, 3 out of stock); invoices collection empty with `counters.invoice.seq = 0`, so the next invoice is INV-0001. `backend/seed.py` remains idempotent for a fresh environment.

## Credentials
No login/auth anywhere — the panel is open (user's explicit choice).

## Notes for testers
- Do NOT click "Print Invoice" buttons in headless runs — they call `window.print()` (native dialog).
- **Dialog width trap**: `components/ui/dialog.tsx` DialogContent ships `sm:max-w-sm` — a bare `max-w-*` prop loses the cascade at ≥640px. Always override with `sm:max-w-*` (builder `sm:max-w-5xl`, view `sm:max-w-4xl`, confirm `sm:max-w-md`).
- Money formatting: `Intl.NumberFormat("en-IN", {currency: "INR"})` → "₹1,234.00".
- "Create Invoice" lives on Dashboard / Products (Sell) / Invoice History — always as a modal, testid `invoice-builder-modal`.

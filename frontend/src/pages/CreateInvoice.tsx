import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileCheck2, Link2, Loader2, Plus, X } from "lucide-react";
import { toast } from "sonner";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import EmptyState from "@/components/ui/EmptyState";
import InvoiceViewModal from "@/components/invoices/InvoiceViewModal";
import ProductPicker from "@/components/invoices/ProductPicker";
import { errorMessage } from "@/lib/errors";
import { formatINR } from "@/lib/format";
import { createInvoice, fetchNextInvoiceNumber, fetchProducts, qk } from "@/lib/queries";
import type { Invoice, Product } from "@/lib/types";

interface ItemRow {
  key: number;
  product_id: string;
  qty: string;
}

const EMPTY_CUSTOMER = {
  customer_name: "",
  company_name: "",
  street_address: "",
  city_pincode: "",
  phone: "",
  email: "",
};

const CUSTOMER_FIELDS: { field: keyof typeof EMPTY_CUSTOMER; label: string; testid: string; placeholder: string }[] = [
  { field: "customer_name", label: "Name", testid: "invoice-customer-name-input", placeholder: "Customer name" },
  { field: "company_name", label: "Company Name", testid: "invoice-company-input", placeholder: "Company name" },
  { field: "street_address", label: "Street Address", testid: "invoice-street-input", placeholder: "Street address" },
  { field: "city_pincode", label: "City, Pincode", testid: "invoice-city-input", placeholder: "City, Pincode" },
  { field: "phone", label: "Phone", testid: "invoice-phone-input", placeholder: "Phone number" },
  { field: "email", label: "Email", testid: "invoice-email-input", placeholder: "Email address" },
];

export default function CreateInvoice() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const preselect = searchParams.get("product") ?? "";

  const productsQuery = useQuery({ queryKey: qk.products, queryFn: fetchProducts });
  const products = productsQuery.data ?? [];
  const nextNumberQuery = useQuery({ queryKey: qk.nextInvoiceNumber, queryFn: fetchNextInvoiceNumber });

  const rowKey = useRef(1);
  const [customer, setCustomer] = useState(EMPTY_CUSTOMER);
  const [date, setDate] = useState("");
  const [discount, setDiscount] = useState("0");
  const [rows, setRows] = useState<ItemRow[]>([{ key: 0, product_id: preselect, qty: "1" }]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [createdInvoice, setCreatedInvoice] = useState<Invoice | null>(null);

  useEffect(() => {
    const nextDate = nextNumberQuery.data?.date;
    if (nextDate) setDate((current) => current || nextDate);
  }, [nextNumberQuery.data?.date]);

  const productById = useMemo(() => new Map(products.map((product) => [product.id, product])), [products]);

  const parsedRows = rows.map((row) => {
    const product = row.product_id ? productById.get(row.product_id) : undefined;
    const qty = Number.parseInt(row.qty, 10) || 0;
    const usedElsewhere = rows
      .filter((other) => other.key !== row.key && other.product_id === row.product_id)
      .reduce((sum, other) => sum + (Number.parseInt(other.qty, 10) || 0), 0);
    const available = product ? product.stock - usedElsewhere : 0;
    const insufficient = Boolean(product) && qty > available;
    const lineTotal = product && qty > 0 ? Math.round(qty * product.unit_price * 100) / 100 : 0;
    return { row, product, qty, available, insufficient, lineTotal };
  });

  const subtotal = Math.round(parsedRows.reduce((sum, entry) => sum + entry.lineTotal, 0) * 100) / 100;
  const discountValue = Number.parseFloat(discount) || 0;
  const discountInvalid = discountValue < 0 || discountValue > subtotal;
  const totalRaw = Math.round((subtotal - discountValue) * 100) / 100;
  const grandTotal = Math.round(totalRaw);
  const roundOff = Math.round((grandTotal - totalRaw) * 100) / 100;

  const canSubmit =
    customer.customer_name.trim().length > 0 &&
    parsedRows.length > 0 &&
    parsedRows.every((entry) => entry.product && entry.qty >= 1 && !entry.insufficient) &&
    !discountInvalid;

  const mutation = useMutation({
    mutationFn: () =>
      createInvoice({
        ...customer,
        date: date || undefined,
        discount: discountValue,
        items: parsedRows
          .filter((entry) => entry.product)
          .map((entry) => ({ product_id: entry.row.product_id, quantity: entry.qty })),
      }),
    onSuccess: async (invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: qk.products }),
        queryClient.invalidateQueries({ queryKey: qk.dashboard }),
        queryClient.invalidateQueries({ queryKey: ["invoices"] }),
      ]);
      toast.success(`Invoice ${invoice.invoice_number} created. Stock updated.`);
      setCustomer(EMPTY_CUSTOMER);
      setDiscount("0");
      rowKey.current += 1;
      setRows([{ key: rowKey.current, product_id: "", qty: "1" }]);
      setConfirmOpen(false);
      setCreatedInvoice(invoice);
    },
    onError: (error) => {
      setConfirmOpen(false);
      toast.error(errorMessage(error, "Could not create the invoice."));
    },
  });

  const setField = (field: keyof typeof EMPTY_CUSTOMER) => (event: ChangeEvent<HTMLInputElement>) =>
    setCustomer((current) => ({ ...current, [field]: event.target.value }));

  const updateRow = (key: number, patch: Partial<ItemRow>) =>
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));

  const addRow = () => {
    rowKey.current += 1;
    setRows((current) => [...current, { key: rowKey.current, product_id: "", qty: "1" }]);
  };

  const removeRow = (key: number) =>
    setRows((current) => (current.length > 1 ? current.filter((row) => row.key !== key) : current));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Create Invoice</h1>
          <p className="text-sm text-slate-500">Billing for wholesale orders. Stock is deducted when the invoice is finalized.</p>
        </div>
        <Link to="/invoices" className={buttonVariants({ variant: "outline" })} data-testid="create-invoice-history-link">
          <Link2 className="h-4 w-4" />
          Invoice History
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Issued To</CardTitle>
              <CardDescription>Customer details printed on the invoice.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              {CUSTOMER_FIELDS.map(({ field, label, testid, placeholder }) => (
                <div key={field} className={field === "street_address" ? "sm:col-span-2" : undefined}>
                  <Label htmlFor={`invoice-${field}`}>{label}</Label>
                  <Input
                    id={`invoice-${field}`}
                    value={customer[field]}
                    onChange={setField(field)}
                    placeholder={placeholder}
                    className="mt-1.5"
                    data-testid={testid}
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Products</CardTitle>
                <CardDescription>Code and unit price fill in automatically from stock.</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={addRow} disabled={products.length === 0} data-testid="invoice-add-item-btn">
                <Plus className="h-4 w-4" />
                Add Item
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {productsQuery.isLoading ? (
                <div className="space-y-3" data-testid="invoice-items-loading">
                  {Array.from({ length: 2 }).map((_, index) => (
                    <div key={index} className="h-16 animate-pulse rounded-lg bg-slate-100" />
                  ))}
                </div>
              ) : products.length === 0 ? (
                <EmptyState
                  icon={Plus}
                  title="No products yet"
                  description="Add products to your stock before creating an invoice."
                  action={
                    <Link to="/products" className={buttonVariants({ size: "sm" })}>
                      Go to products
                    </Link>
                  }
                  testid="invoice-items-empty-state"
                />
              ) : (
                parsedRows.map(({ row, product, qty, available, insufficient, lineTotal }, index) => (
                  <div key={row.key} className="rounded-lg border border-slate-200 p-3">
                    <div className="grid gap-3 md:grid-cols-12 md:items-end">
                      <div className="md:col-span-5">
                        <Label className="text-xs text-slate-500">Product</Label>
                        <div className="mt-1.5">
                          <ProductPicker
                            products={products}
                            value={row.product_id}
                            onSelect={(selected: Product) => updateRow(row.key, { product_id: selected.id })}
                            testid={`invoice-item-select-${index}`}
                          />
                        </div>
                      </div>
                      <div className="md:col-span-2">
                        <Label className="text-xs text-slate-500">Code</Label>
                        <div
                          className="mt-1.5 flex h-9 items-center rounded-md border bg-slate-50 px-3 font-mono text-xs text-slate-500"
                          data-testid={`invoice-item-code-${index}`}
                        >
                          {product?.code ?? "-"}
                        </div>
                      </div>
                      <div className="md:col-span-1">
                        <Label className="text-xs text-slate-500">Qty</Label>
                        <Input
                          type="number"
                          min={1}
                          step={1}
                          value={row.qty}
                          onChange={(event) => updateRow(row.key, { qty: event.target.value })}
                          className="mt-1.5"
                          data-testid={`invoice-item-qty-${index}`}
                        />
                      </div>
                      <div className="md:col-span-2">
                        <Label className="text-xs text-slate-500">Unit Price (₹)</Label>
                        <div
                          className="mt-1.5 flex h-9 items-center rounded-md border bg-slate-50 px-3 text-sm tabular-nums"
                          data-testid={`invoice-item-price-${index}`}
                        >
                          {product ? formatINR(product.unit_price) : "-"}
                        </div>
                      </div>
                      <div className="flex items-end justify-between gap-2 md:col-span-2">
                        <div>
                          <Label className="text-xs text-slate-500">Total (₹)</Label>
                          <div
                            className="mt-1.5 flex h-9 items-center px-1 text-sm font-semibold tabular-nums"
                            data-testid={`invoice-item-total-${index}`}
                          >
                            {product ? formatINR(lineTotal) : "-"}
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Remove item"
                          onClick={() => removeRow(row.key)}
                          disabled={rows.length === 1}
                          data-testid={`invoice-item-remove-${index}`}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    {product && insufficient ? (
                      <p className="mt-2 text-xs font-medium text-rose-600" data-testid={`invoice-item-warning-${index}`}>
                        Insufficient stock available. Only {available} left in stock.
                      </p>
                    ) : product ? (
                      <p className="mt-2 text-xs text-slate-400">Available stock: {available}</p>
                    ) : null}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Invoice Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-2">
                <Label>Invoice Number</Label>
                <div
                  className="flex h-9 items-center rounded-md border bg-[#F4EFE6] px-3 text-sm font-bold tracking-wide"
                  data-testid="invoice-number-display"
                >
                  {nextNumberQuery.isLoading ? "..." : nextNumberQuery.data?.invoice_number ?? "-"}
                </div>
                <p className="text-xs text-slate-400">Assigned automatically. Duplicate numbers are not possible.</p>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="invoice-date">Invoice Date</Label>
                <Input
                  id="invoice-date"
                  type="date"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                  data-testid="invoice-date-input"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between py-1 text-sm">
                <span className="text-slate-500">Subtotal</span>
                <span className="font-medium tabular-nums" data-testid="invoice-subtotal-display">
                  {formatINR(subtotal)}
                </span>
              </div>
              <div className="grid gap-2 py-2">
                <Label htmlFor="invoice-discount">Discount (₹)</Label>
                <Input
                  id="invoice-discount"
                  type="number"
                  min={0}
                  step="0.01"
                  value={discount}
                  onChange={(event) => setDiscount(event.target.value)}
                  data-testid="invoice-discount-input"
                />
                {discountInvalid ? (
                  <p className="text-xs font-medium text-rose-600" data-testid="invoice-discount-error">
                    Discount cannot exceed the subtotal.
                  </p>
                ) : null}
              </div>
              {roundOff !== 0 ? (
                <div className="flex items-center justify-between py-1 text-sm">
                  <span className="text-slate-500">Round-Off</span>
                  <span className="font-medium tabular-nums" data-testid="invoice-roundoff-display">
                    {formatINR(roundOff)}
                  </span>
                </div>
              ) : null}
              <div className="mt-2 flex items-center justify-between rounded-lg bg-slate-100 px-4 py-3">
                <span className="text-sm font-semibold text-slate-700">Total</span>
                <span className="text-lg font-bold tabular-nums text-slate-900" data-testid="invoice-total-display">
                  {formatINR(grandTotal)}
                </span>
              </div>
              <Button
                className="mt-4 w-full"
                onClick={() => setConfirmOpen(true)}
                disabled={!canSubmit || mutation.isPending}
                data-testid="invoice-submit-btn"
              >
                {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCheck2 className="h-4 w-4" />}
                Finalize Invoice
              </Button>
              <p className="mt-2 text-center text-xs text-slate-400">Stock is deducted only after you finalize.</p>
            </CardContent>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Finalize invoice?"
        description={`Stock will be deducted and ${nextNumberQuery.data?.invoice_number ?? "the invoice"} saved to history. This cannot be undone.`}
        confirmLabel="Finalize & Save"
        loading={mutation.isPending}
        onConfirm={() => mutation.mutate()}
      />
      <InvoiceViewModal invoice={createdInvoice} onOpenChange={(open) => { if (!open) setCreatedInvoice(null); }} />
    </div>
  );
}

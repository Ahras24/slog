import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, FilePlus2, Printer, Receipt, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import EmptyState from "@/components/ui/EmptyState";
import InvoiceBuilderModal from "@/components/invoices/InvoiceBuilderModal";
import InvoiceViewModal from "@/components/invoices/InvoiceViewModal";
import PrintPortal from "@/components/invoices/PrintPortal";
import { errorMessage } from "@/lib/errors";
import { deleteInvoice, fetchInvoices, qk } from "@/lib/queries";
import { formatDateShort, formatINR } from "@/lib/format";
import type { Invoice } from "@/lib/types";

export default function InvoiceHistory() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [builderOpen, setBuilderOpen] = useState(false);

  const filters = useMemo(() => ({ search, date_from: from, date_to: to }), [search, from, to]);
  const invoicesQuery = useQuery({ queryKey: qk.invoices(filters), queryFn: () => fetchInvoices(filters) });
  const invoices = invoicesQuery.data;

  const [viewInvoice, setViewInvoice] = useState<Invoice | null>(null);
  const [printInvoice, setPrintInvoice] = useState<Invoice | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Invoice | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (invoice: Invoice) => deleteInvoice(invoice.id),
    onSuccess: async (_data, invoice) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["invoices"] }),
        queryClient.invalidateQueries({ queryKey: qk.dashboard }),
      ]);
      toast.success(`Invoice ${invoice.invoice_number} deleted`);
      setDeleteTarget(null);
    },
    onError: (error) => toast.error(errorMessage(error, "Could not delete the invoice.")),
  });

  const hasFilters = Boolean(search || from || to);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Invoice History</h1>
          <p className="text-sm text-slate-500">Every finalized invoice, stored exactly as it was created.</p>
        </div>
        <Button variant="outline" onClick={() => setBuilderOpen(true)} data-testid="history-create-invoice-btn">
          <FilePlus2 className="h-4 w-4" />
          Create Invoice
        </Button>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-end gap-3 border-b border-slate-200 p-4">
          <div className="relative w-full sm:w-64">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search invoice no. or customer"
              className="pl-9"
              data-testid="invoice-search-input"
            />
          </div>
          <div className="grid gap-1">
            <Label className="text-xs text-slate-500">From</Label>
            <Input
              type="date"
              value={from}
              onChange={(event) => setFrom(event.target.value)}
              className="w-40"
              data-testid="invoice-date-from"
            />
          </div>
          <div className="grid gap-1">
            <Label className="text-xs text-slate-500">To</Label>
            <Input
              type="date"
              value={to}
              onChange={(event) => setTo(event.target.value)}
              className="w-40"
              data-testid="invoice-date-to"
            />
          </div>
          {hasFilters ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearch("");
                setFrom("");
                setTo("");
              }}
              data-testid="invoice-filters-clear"
            >
              Clear filters
            </Button>
          ) : null}
        </div>

        {invoicesQuery.isLoading ? (
          <div className="space-y-3 p-4" data-testid="invoice-history-loading">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-10 animate-pulse rounded-md bg-slate-100" />
            ))}
          </div>
        ) : (invoices ?? []).length === 0 ? (
          hasFilters ? (
            <EmptyState
              icon={Search}
              title="No invoices found"
              description="No invoices match the current search or date range."
              testid="invoices-search-empty-state"
            />
          ) : (
            <EmptyState
              icon={Receipt}
              title="No invoices yet"
              description="Create your first invoice to see it stored here with its original details."
              action={
                <Button size="sm" onClick={() => setBuilderOpen(true)} data-testid="invoices-empty-create-btn">
                  Create Invoice
                </Button>
              }
              testid="invoices-empty-state"
            />
          )
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50/60 hover:bg-slate-50/60">
                <TableHead>Invoice No.</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead className="text-right">Products</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(invoices ?? []).map((invoice) => (
                <TableRow key={invoice.id} data-testid={`invoice-row-${invoice.invoice_number}`}>
                  <TableCell className="font-semibold text-[#0F2942]">{invoice.invoice_number}</TableCell>
                  <TableCell className="text-slate-600">{formatDateShort(invoice.date)}</TableCell>
                  <TableCell>
                    <div className="font-medium text-slate-900">{invoice.customer_name}</div>
                    {invoice.company_name ? <div className="text-xs text-slate-500">{invoice.company_name}</div> : null}
                  </TableCell>
                  <TableCell className="text-right text-slate-700">{invoice.items.length}</TableCell>
                  <TableCell className="text-right font-medium tabular-nums text-slate-900">
                    {formatINR(invoice.total)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" data-testid="invoice-status-badge">
                      {invoice.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        title="View invoice"
                        onClick={() => setViewInvoice(invoice)}
                        data-testid={`view-invoice-btn-${invoice.invoice_number}`}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        title="Print invoice"
                        onClick={() => setPrintInvoice(invoice)}
                        data-testid={`reprint-invoice-btn-${invoice.invoice_number}`}
                      >
                        <Printer className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        title="Delete invoice"
                        className="text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                        onClick={() => setDeleteTarget(invoice)}
                        data-testid={`delete-invoice-btn-${invoice.invoice_number}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
      <p className="text-xs text-slate-400">
        Invoice history preserves the original product names, codes and prices even if products change later.
      </p>

      <InvoiceBuilderModal open={builderOpen} onOpenChange={setBuilderOpen} />
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title={`Delete invoice ${deleteTarget?.invoice_number ?? ""}?`}
        description={`This permanently removes the invoice record for ${deleteTarget?.customer_name ?? "this customer"} (${formatINR(deleteTarget?.total ?? 0)}). Stock stays as it is — use Add Stock if the goods came back. This cannot be undone.`}
        confirmLabel="Delete Invoice"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget);
        }}
      />
      <InvoiceViewModal
        invoice={viewInvoice}
        onOpenChange={(open) => {
          if (!open) setViewInvoice(null);
        }}
      />
      {printInvoice ? <PrintPortal invoice={printInvoice} onDone={() => setPrintInvoice(null)} /> : null}
    </div>
  );
}

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, AlertTriangle, FilePlus2, IndianRupee, Layers, Package, Receipt } from "lucide-react";
import { Button } from "@/components/ui/button";
import SummaryCard from "@/components/dashboard/SummaryCard";
import InvoiceBuilderModal from "@/components/invoices/InvoiceBuilderModal";
import { fetchDashboard, qk } from "@/lib/queries";

export default function Dashboard() {
  const summaryQuery = useQuery({ queryKey: qk.dashboard, queryFn: fetchDashboard });
  const [builderOpen, setBuilderOpen] = useState(false);
  const summary = summaryQuery.data;
  const summaryLoading = summaryQuery.isLoading;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
          <p className="mt-1 text-base text-slate-500">Stock and billing overview for your store.</p>
        </div>
        <Button size="lg" onClick={() => setBuilderOpen(true)} data-testid="dashboard-create-invoice-btn">
          <FilePlus2 className="h-5 w-5" />
          Create Invoice
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-5 md:grid-cols-3">
        <SummaryCard
          testid="metric-total-products"
          label="Total Products"
          value={summary ? summary.total_products : "-"}
          icon={Package}
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-total-stock"
          label="Total Stock"
          value={summary ? summary.total_stock : "-"}
          icon={Layers}
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-low-stock"
          label="Low Stock"
          value={summary ? summary.low_stock : "-"}
          icon={AlertTriangle}
          tone="text-amber-500"
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-out-of-stock"
          label="Out of Stock"
          value={summary ? summary.out_of_stock : "-"}
          icon={AlertOctagon}
          tone="text-rose-500"
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-today-sales"
          label="Today's Sales"
          value={summary ? formatTodaySales(summary.today_sales) : "-"}
          icon={IndianRupee}
          tone="text-emerald-600"
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-today-invoices"
          label="Today's Invoices"
          value={summary ? summary.today_invoice_count : "-"}
          icon={Receipt}
          loading={summaryLoading}
        />
      </div>

      <InvoiceBuilderModal open={builderOpen} onOpenChange={setBuilderOpen} />
    </div>
  );
}

function formatTodaySales(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

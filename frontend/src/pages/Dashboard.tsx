import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, AlertTriangle, FilePlus2, IndianRupee, Layers, Package, Receipt } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import SummaryCard from "@/components/dashboard/SummaryCard";
import StockTable from "@/components/products/StockTable";
import ProductFormModal from "@/components/products/ProductFormModal";
import AddStockModal from "@/components/products/AddStockModal";
import { fetchDashboard, fetchProducts, qk } from "@/lib/queries";
import { formatINR } from "@/lib/format";
import type { Product } from "@/lib/types";

export default function Dashboard() {
  const navigate = useNavigate();
  const summaryQuery = useQuery({ queryKey: qk.dashboard, queryFn: fetchDashboard });
  const productsQuery = useQuery({ queryKey: qk.products, queryFn: fetchProducts });

  const [formOpen, setFormOpen] = useState(false);
  const [editProduct, setEditProduct] = useState<Product | null>(null);
  const [stockOpen, setStockOpen] = useState(false);
  const [stockProduct, setStockProduct] = useState<Product | null>(null);

  const summary = summaryQuery.data;
  const summaryLoading = summaryQuery.isLoading;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">Stock and billing overview for your store.</p>
        </div>
        <Link to="/invoices/new" className={buttonVariants()} data-testid="dashboard-create-invoice-btn">
          <FilePlus2 className="h-4 w-4" />
          Create Invoice
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
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
          value={summary ? formatINR(summary.today_sales) : "-"}
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

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">Stock Management</h2>
          <Link
            to="/products"
            className="text-sm font-medium text-[#0F2942] hover:underline"
            data-testid="dashboard-view-all-products-link"
          >
            Go to products page
          </Link>
        </div>
        <StockTable
          products={productsQuery.data}
          isLoading={productsQuery.isLoading}
          onEdit={(product) => {
            setEditProduct(product);
            setFormOpen(true);
          }}
          onAddStock={(product) => {
            setStockProduct(product);
            setStockOpen(true);
          }}
          onSell={(product) => navigate(`/invoices/new?product=${product.id}`)}
          emptyAction={
            <Link to="/products" className={buttonVariants({ variant: "outline", size: "sm" })}>
              Go to products
            </Link>
          }
        />
      </div>

      <ProductFormModal open={formOpen} onOpenChange={setFormOpen} product={editProduct} />
      <AddStockModal open={stockOpen} onOpenChange={setStockOpen} product={stockProduct} />
    </div>
  );
}

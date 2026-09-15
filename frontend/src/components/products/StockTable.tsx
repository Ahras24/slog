import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Package, PackagePlus, Pencil, Receipt, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import EmptyState from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/products/StatusBadge";
import { formatINR } from "@/lib/format";
import type { Product, StockFilter } from "@/lib/types";
import { cn } from "@/lib/utils";

const FILTERS: { value: StockFilter; label: string; testid: string }[] = [
  { value: "all", label: "All", testid: "filter-tab-all" },
  { value: "in_stock", label: "In Stock", testid: "filter-tab-in-stock" },
  { value: "low_stock", label: "Low Stock", testid: "filter-tab-low-stock" },
  { value: "out_of_stock", label: "Out of Stock", testid: "filter-tab-out-of-stock" },
];

interface StockTableProps {
  products: Product[] | undefined;
  isLoading: boolean;
  onEdit: (product: Product) => void;
  onAddStock: (product: Product) => void;
  onSell: (product: Product) => void;
  emptyAction?: ReactNode;
}

// Reusable stock table: shared by the Dashboard and the Products & Stock page.
export default function StockTable({ products, isLoading, onEdit, onAddStock, onSell, emptyAction }: StockTableProps) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<StockFilter>("all");

  const counts = useMemo(() => {
    const list = products ?? [];
    return {
      all: list.length,
      in_stock: list.filter((p) => p.status === "in_stock").length,
      low_stock: list.filter((p) => p.status === "low_stock").length,
      out_of_stock: list.filter((p) => p.status === "out_of_stock").length,
    };
  }, [products]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (products ?? []).filter((product) => {
      if (filter !== "all" && product.status !== filter) return false;
      if (!term) return true;
      return product.name.toLowerCase().includes(term) || product.code.toLowerCase().includes(term);
    });
  }, [products, search, filter]);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by product name or code"
            className="pl-9"
            data-testid="stock-search-input"
          />
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
          {FILTERS.map(({ value, label, testid }) => (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors duration-150",
                filter === value ? "bg-white text-[#0F2942] shadow-sm" : "text-slate-500 hover:text-slate-800"
              )}
              data-testid={testid}
            >
              {label} ({counts[value]})
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3 p-4" data-testid="stock-table-loading">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-10 animate-pulse rounded-md bg-slate-100" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        (products ?? []).length === 0 ? (
          <EmptyState
            icon={Package}
            title="No products yet"
            description="Add your first product to start tracking stock and creating invoices."
            action={emptyAction}
            testid="products-empty-state"
          />
        ) : (
          <EmptyState
            icon={Search}
            title="No products found"
            description="No products match the current search or filter. Try a different term."
            action={
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearch("");
                  setFilter("all");
                }}
                data-testid="stock-clear-filters-button"
              >
                Clear search &amp; filters
              </Button>
            }
            testid="stock-search-empty-state"
          />
        )
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50/60 hover:bg-slate-50/60">
              <TableHead>Product</TableHead>
              <TableHead>Code</TableHead>
              <TableHead className="text-right">Stock</TableHead>
              <TableHead className="text-right">Unit Price</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((product) => (
              <TableRow key={product.id} data-testid={`product-row-${product.code}`}>
                <TableCell className="font-medium text-slate-900">{product.name}</TableCell>
                <TableCell className="font-mono text-xs text-slate-500">{product.code}</TableCell>
                <TableCell className="text-right">
                  <span
                    className={cn(
                      "font-semibold",
                      product.stock === 0 ? "text-rose-600" : product.stock <= 10 ? "text-amber-600" : "text-slate-900"
                    )}
                  >
                    {product.stock}
                  </span>
                </TableCell>
                <TableCell className="text-right text-slate-700">{formatINR(product.unit_price)}</TableCell>
                <TableCell>
                  <StatusBadge status={product.status} />
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="Edit product"
                      onClick={() => onEdit(product)}
                      data-testid={`edit-product-btn-${product.code}`}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="Add stock"
                      onClick={() => onAddStock(product)}
                      data-testid={`add-stock-btn-${product.code}`}
                    >
                      <PackagePlus className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title="Create invoice / sell"
                      onClick={() => onSell(product)}
                      data-testid={`sell-product-btn-${product.code}`}
                    >
                      <Receipt className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

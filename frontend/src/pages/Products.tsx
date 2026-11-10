import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import StockTable from "@/components/products/StockTable";
import ProductFormModal from "@/components/products/ProductFormModal";
import AddStockModal from "@/components/products/AddStockModal";
import InvoiceBuilderModal from "@/components/invoices/InvoiceBuilderModal";
import { fetchProducts, qk } from "@/lib/queries";
import type { Product } from "@/lib/types";

function hasAddProductRequest(state: unknown): boolean {
  return (
    typeof state === "object" &&
    state !== null &&
    "openAddProduct" in state &&
    state.openAddProduct === true
  );
}

export default function Products() {
  const location = useLocation();
  const navigate = useNavigate();
  const productsQuery = useQuery({ queryKey: qk.products, queryFn: fetchProducts });

  const [formOpen, setFormOpen] = useState(false);
  const [editProduct, setEditProduct] = useState<Product | null>(null);
  const [stockOpen, setStockOpen] = useState(false);
  const [stockProduct, setStockProduct] = useState<Product | null>(null);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [sellProductId, setSellProductId] = useState<string | undefined>(undefined);

  const openAddProduct = useCallback(() => {
    setEditProduct(null);
    setFormOpen(true);
  }, []);

  useEffect(() => {
    if (!hasAddProductRequest(location.state)) return;

    if (!formOpen) openAddProduct();
    navigate(`${location.pathname}${location.search}${location.hash}`, {
      replace: true,
      state: null,
    });
  }, [formOpen, location.hash, location.pathname, location.search, location.state, navigate, openAddProduct]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Products &amp; Stock</h1>
          <p className="text-sm text-slate-500">Manage products, prices and stock levels.</p>
        </div>
        <Button
          onClick={openAddProduct}
          data-testid="add-product-btn"
        >
          <Plus className="h-4 w-4" />
          Add Product
          <span
            aria-hidden="true"
            className="ml-1 rounded border border-current/30 px-1 py-0.5 text-[10px] leading-none opacity-0 transition-opacity group-hover/button:opacity-100 group-focus-visible/button:opacity-100"
          >
            F2
          </span>
        </Button>
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
        onSell={(product) => {
          setSellProductId(product.id);
          setBuilderOpen(true);
        }}
        emptyAction={
          <Button
            size="sm"
            onClick={openAddProduct}
            data-testid="empty-add-product-btn"
          >
            <Plus className="h-4 w-4" />
            Add first product
          </Button>
        }
      />

      <ProductFormModal open={formOpen} onOpenChange={setFormOpen} product={editProduct} />
      <AddStockModal open={stockOpen} onOpenChange={setStockOpen} product={stockProduct} />
      <InvoiceBuilderModal open={builderOpen} onOpenChange={setBuilderOpen} preselectProductId={sellProductId} />
    </div>
  );
}

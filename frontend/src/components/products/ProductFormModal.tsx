import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/lib/errors";
import { createProduct, deleteProduct, qk, updateProduct } from "@/lib/queries";
import type { Product } from "@/lib/types";

interface ProductFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  product?: Product | null; // null/undefined → create mode
}

// Shared add/edit product form — the same modal handles both modes.
export default function ProductFormModal({ open, onOpenChange, product }: ProductFormModalProps) {
  const queryClient = useQueryClient();
  const isEdit = Boolean(product);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [stock, setStock] = useState("0");
  const [price, setPrice] = useState("");
  const [codeError, setCodeError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (open) {
      setName(product?.name ?? "");
      setCode(product?.code ?? "");
      setStock(String(product?.stock ?? 0));
      setPrice(product ? String(product.unit_price) : "");
      setCodeError("");
      setConfirmDelete(false);
    }
  }, [open, product]);

  const saveMutation = useMutation({
    mutationFn: () => {
      const body = {
        name: name.trim(),
        code: code.trim(),
        stock: Number.parseInt(stock, 10) || 0,
        unit_price: Number.parseFloat(price) || 0,
      };
      return isEdit && product ? updateProduct(product.id, body) : createProduct(body);
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: qk.products });
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
      toast.success(isEdit ? "Product updated" : `Product "${saved.name}" added`);
      onOpenChange(false);
    },
    onError: (error) => {
      const message = errorMessage(error, "Could not save the product.");
      if (error instanceof ApiError && error.status === 409) setCodeError(message);
      toast.error(message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => (product ? deleteProduct(product.id) : Promise.resolve()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.products });
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
      toast.success("Product deleted");
      setConfirmDelete(false);
      onOpenChange(false);
    },
    onError: (error) => toast.error(errorMessage(error, "Could not delete the product.")),
  });

  const parsedStock = Number.parseInt(stock, 10);
  const parsedPrice = Number.parseFloat(price);
  const valid =
    name.trim().length > 0 &&
    code.trim().length > 0 &&
    Number.isInteger(parsedStock) &&
    parsedStock >= 0 &&
    Number.isFinite(parsedPrice) &&
    parsedPrice >= 0;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg" data-testid="product-form-modal">
          <DialogHeader>
            <DialogTitle>{isEdit ? "Edit Product" : "Add Product"}</DialogTitle>
            <DialogDescription>
              {isEdit
                ? "Update the product details below. Past invoices keep their original details."
                : "Fill in the details to add a new product to stock."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="product-name">Product Name</Label>
              <Input
                id="product-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Cotton Oxford Shirt"
                data-testid="product-name-input"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="product-code">Product Code</Label>
              <Input
                id="product-code"
                value={code}
                onChange={(event) => {
                  setCode(event.target.value);
                  setCodeError("");
                }}
                placeholder="e.g. SHIRT-OXF-01"
                className={codeError ? "border-rose-400" : undefined}
                data-testid="product-code-input"
              />
              {codeError ? (
                <p className="text-xs font-medium text-rose-600" data-testid="product-code-error">
                  {codeError}
                </p>
              ) : null}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="product-stock">Stock Count</Label>
                <Input
                  id="product-stock"
                  type="number"
                  min={0}
                  step={1}
                  value={stock}
                  onChange={(event) => setStock(event.target.value)}
                  data-testid="product-stock-input"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="product-price">Unit Price (₹)</Label>
                <Input
                  id="product-price"
                  type="number"
                  min={0}
                  step="0.01"
                  value={price}
                  onChange={(event) => setPrice(event.target.value)}
                  placeholder="0.00"
                  data-testid="product-price-input"
                />
              </div>
            </div>
          </div>
          <DialogFooter className={isEdit ? "sm:justify-between" : undefined}>
            {isEdit ? (
              <Button
                variant="ghost"
                className="text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                onClick={() => setConfirmDelete(true)}
                data-testid="product-delete-button"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            ) : (
              <span />
            )}
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={!valid || saveMutation.isPending}
              data-testid="product-save-button"
            >
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save Product
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete product?"
        description={`"${product?.name ?? ""}" will be permanently removed from stock. Past invoices keep their original details.`}
        confirmLabel="Delete Product"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
      />
    </>
  );
}

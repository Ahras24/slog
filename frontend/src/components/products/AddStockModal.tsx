import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
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
import { errorMessage } from "@/lib/errors";
import { addStock, qk } from "@/lib/queries";
import type { Product } from "@/lib/types";

interface AddStockModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  product: Product | null;
}

export default function AddStockModal({ open, onOpenChange, product }: AddStockModalProps) {
  const queryClient = useQueryClient();
  const [additional, setAdditional] = useState("1");

  useEffect(() => {
    if (open) setAdditional("1");
  }, [open, product]);

  const quantity = Number.parseInt(additional, 10) || 0;
  const updatedStock = (product?.stock ?? 0) + Math.max(quantity, 0);

  const mutation = useMutation({
    mutationFn: () => {
      if (!product) throw new Error("No product selected.");
      return addStock(product.id, quantity);
    },
    onSuccess: (updatedProduct) => {
      queryClient.invalidateQueries({ queryKey: qk.products });
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
      toast.success(`Stock updated — ${updatedProduct.name}: ${updatedProduct.stock} units`);
      onOpenChange(false);
    },
    onError: (error) => toast.error(errorMessage(error, "Could not update stock.")),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="add-stock-modal">
        <DialogHeader>
          <DialogTitle>Update Stock</DialogTitle>
          <DialogDescription>
            {product ? `${product.name} (${product.code})` : "Select a product"}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label>Current Stock</Label>
              <div
                className="flex h-9 items-center rounded-md border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700"
                data-testid="stock-current-preview"
              >
                {product?.stock ?? 0}
              </div>
            </div>
            <div className="grid gap-2">
              <Label>Updated Stock</Label>
              <div
                className="flex h-9 items-center rounded-md border border-slate-200 bg-[#0F2942]/5 px-3 text-sm font-bold text-[#0F2942]"
                data-testid="stock-updated-preview"
              >
                {updatedStock}
              </div>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="additional-stock">Additional Stock Quantity</Label>
            <Input
              id="additional-stock"
              type="number"
              min={1}
              step={1}
              value={additional}
              onChange={(event) => setAdditional(event.target.value)}
              data-testid="stock-additional-input"
            />
            {quantity <= 0 ? (
              <p className="text-xs font-medium text-rose-600" data-testid="stock-additional-error">
                Enter a quantity greater than zero.
              </p>
            ) : null}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="stock-cancel-button">
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={quantity <= 0 || mutation.isPending}
            data-testid="stock-save-button"
          >
            {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save Stock
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

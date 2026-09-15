import { Badge } from "@/components/ui/badge";
import { STOCK_STATUS_LABELS } from "@/lib/format";
import type { StockStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<StockStatus, string> = {
  in_stock: "bg-emerald-50 text-emerald-700 border-emerald-200",
  low_stock: "bg-amber-50 text-amber-700 border-amber-200",
  out_of_stock: "bg-rose-50 text-rose-700 border-rose-200",
};

export function StatusBadge({ status }: { status: StockStatus }) {
  const style = STYLES[status] ?? STYLES.in_stock;
  return (
    <Badge variant="outline" className={cn("border bg-clip-padding font-medium", style)} data-testid={`status-badge-${status}`}>
      {STOCK_STATUS_LABELS[status] ?? status}
    </Badge>
  );
}

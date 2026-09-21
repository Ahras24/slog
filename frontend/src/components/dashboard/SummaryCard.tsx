import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface SummaryCardProps {
  testid: string;
  label: string;
  value?: string | number;
  icon: LucideIcon;
  tone?: string;
  background?: string;
  loading?: boolean;
}

export default function SummaryCard({
  testid,
  label,
  value,
  icon: Icon,
  tone = "text-slate-500",
  background = "bg-white",
  loading = false,
}: SummaryCardProps) {
  return (
    <div className={cn("flex flex-col justify-between gap-3 rounded-xl border border-slate-200 p-4 shadow-sm", background)} data-testid={testid}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</span>
        <Icon className={cn("h-4 w-4 shrink-0", tone)} />
      </div>
      {loading ? (
        <div className="h-7 w-16 animate-pulse rounded bg-slate-100" data-testid="summary-card-skeleton" />
      ) : (
        <span className="text-2xl font-bold tracking-tight text-slate-900">{value}</span>
      )}
    </div>
  );
}

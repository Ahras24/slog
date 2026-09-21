import { useEffect, useState } from "react";
import { ChevronsUpDown, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { Product } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ProductPickerProps {
  products: Product[];
  value: string;
  onSelect: (product: Product) => void;
  testid: string;
}

// Searchable product selector for invoice line items — picking a product auto-fills code and unit price.
export default function ProductPicker({ products, value, onSelect, testid }: ProductPickerProps) {
  const [open, setOpen] = useState(false);
  const [term, setTerm] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const selected = products.find((product) => product.id === value);
  const filtered = products.filter((product) => {
    const query = term.trim().toLowerCase();
    if (!query) return true;
    return product.name.toLowerCase().includes(query) || product.code.toLowerCase().includes(query);
  });

  useEffect(() => {
    setHighlightedIndex(0);
  }, [term, open]);

  const selectProduct = (product: Product) => {
    onSelect(product);
    setOpen(false);
    setTerm("");
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className={cn(
          "flex h-9 w-full items-center justify-between gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm transition-colors duration-150 hover:bg-slate-50",
          selected ? "text-slate-900" : "text-slate-400"
        )}
        data-testid={testid}
        data-enter-field
        onClick={() => setHighlightedIndex(0)}
      >
        <span className="truncate">{selected ? selected.name : "Select product"}</span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-slate-400" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-80 p-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <Input
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setHighlightedIndex((current) => (filtered.length ? (current + 1) % filtered.length : 0));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setHighlightedIndex((current) => (filtered.length ? (current - 1 + filtered.length) % filtered.length : 0));
              } else if (event.key === "Enter") {
                event.preventDefault();
                const product = filtered[highlightedIndex];
                if (product) selectProduct(product);
              } else if (event.key === "Escape") {
                event.preventDefault();
                setOpen(false);
              }
            }}
            placeholder="Search name or code"
            className="h-8 pl-8 text-xs"
            data-testid="product-picker-search"
          />
        </div>
        <div className="mt-2 max-h-56 overflow-y-auto">
          {filtered.map((product) => (
            <button
              key={product.id}
              type="button"
              onClick={() => {
                selectProduct(product);
              }}
              className={cn(
                "flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors duration-150 hover:bg-slate-100",
                product.id === value && "bg-slate-50",
                filtered.indexOf(product) === highlightedIndex && "bg-slate-100"
              )}
              onMouseEnter={() => setHighlightedIndex(filtered.indexOf(product))}
              data-testid={`product-picker-option-${product.code}`}
            >
              <span className="truncate">{product.name}</span>
              <span className="shrink-0 font-mono text-xs text-slate-400">{product.code}</span>
            </button>
          ))}
          {filtered.length === 0 ? (
            <div className="px-2 py-6 text-center text-xs text-slate-400">No products found</div>
          ) : null}
        </div>
      </PopoverContent>
    </Popover>
  );
}

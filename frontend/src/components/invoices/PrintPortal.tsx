import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import InvoiceSheet from "@/components/invoices/InvoiceSheet";
import type { Invoice } from "@/lib/types";

interface PrintPortalProps {
  invoice: Invoice;
  onDone: () => void;
}

// Mounts the A4 sheet outside the app root; print CSS shows only #invoice-print-root.
export default function PrintPortal({ invoice, onDone }: PrintPortalProps) {
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (cancelled) return;
      try {
        window.print();
      } catch {
        // Headless environments may not implement the print dialog.
      }
      onDoneRef.current();
    }, 200);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [invoice]);

  return createPortal(
    <div id="invoice-print-root">
      <div className="w-[210mm] bg-white p-[18mm]">
        <InvoiceSheet invoice={invoice} />
      </div>
    </div>,
    document.body
  );
}

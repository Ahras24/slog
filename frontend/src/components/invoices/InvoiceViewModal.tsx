import { useState } from "react";
import { Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import InvoiceSheet from "@/components/invoices/InvoiceSheet";
import PrintPortal from "@/components/invoices/PrintPortal";
import type { Invoice } from "@/lib/types";

interface InvoiceViewModalProps {
  invoice: Invoice | null;
  onOpenChange: (open: boolean) => void;
}

// Shows the stored invoice snapshot exactly as it was created, with a print action.
export default function InvoiceViewModal({ invoice, onOpenChange }: InvoiceViewModalProps) {
  const [printing, setPrinting] = useState(false);
  if (!invoice) return null;

  return (
    <>
      <Dialog open={Boolean(invoice)} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-4xl" data-testid="invoice-view-modal">
          <DialogHeader>
            <DialogTitle>Invoice {invoice.invoice_number}</DialogTitle>
          </DialogHeader>
          <div
            className="max-h-[70vh] overflow-auto rounded-lg border border-slate-200 bg-slate-100 p-3 sm:p-5"
            data-testid="invoice-sheet-preview"
          >
            {/* True A4 width (210mm with 18mm page padding) so the preview matches the printout 1:1 */}
            <div className="mx-auto w-[210mm] bg-white shadow-sm">
              <div className="p-[18mm]">
                <InvoiceSheet invoice={invoice} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="invoice-view-close-button">
              Close
            </Button>
            <Button onClick={() => setPrinting(true)} data-testid="print-invoice-btn">
              <Printer className="h-4 w-4" />
              Print Invoice
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {printing ? <PrintPortal invoice={invoice} onDone={() => setPrinting(false)} /> : null}
    </>
  );
}

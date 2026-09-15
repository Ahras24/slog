import type { Invoice } from "@/lib/types";
import { formatINR, formatInvoiceDate } from "@/lib/format";

function TotalsRow({ label, value, testid }: { label: string; value: string; testid?: string }) {
  return (
    <div className="flex items-center justify-between gap-6 py-1 text-sm" data-testid={testid}>
      <span className="text-[#6B7280]">{label}</span>
      <span className="font-semibold tabular-nums text-[#111827]">{value}</span>
    </div>
  );
}

// A4 print-ready invoice sheet — visual match for the store's reference invoice.
// No page chrome here: the screen modal and the print portal supply their own padding.
export default function InvoiceSheet({ invoice }: { invoice: Invoice }) {
  const issuedLines = [
    invoice.company_name,
    invoice.street_address,
    invoice.city_pincode,
    invoice.phone,
    invoice.email,
  ].filter((line) => line.trim().length > 0);

  return (
    <div className="font-invoice bg-white text-[#111827]" data-testid="invoice-sheet">
      <div className="flex items-start justify-between gap-6">
        <h1 className="text-2xl font-extrabold tracking-[0.2em]">INVOICE</h1>
        <div className="text-right">
          <div className="inline-flex items-baseline gap-2 rounded-md bg-[#F4EFE6] px-4 py-2">
            <span className="text-xs text-[#6B7280]">Invoice No.</span>
            <span className="text-sm font-bold tracking-wide" data-testid="invoice-sheet-number">
              {invoice.invoice_number}
            </span>
          </div>
          <div className="mt-2 text-sm font-bold">{formatInvoiceDate(invoice.date)}</div>
        </div>
      </div>

      <div className="mt-8 text-sm leading-relaxed">
        <div className="text-xs font-bold uppercase tracking-wider text-[#6B7280]">Issued to:</div>
        <div className="mt-1 font-semibold">{invoice.customer_name}</div>
        {issuedLines.map((line, index) => (
          <div key={`${index}-${line}`} className="text-[#374151]">
            {line}
          </div>
        ))}
      </div>

      <table className="mt-8 w-full border-collapse text-[13px]">
        <thead>
          <tr className="bg-[#F7F3EB]">
            <th className="w-[38%] border border-[#D1D5DB] px-4 py-2.5 text-left font-semibold">Product</th>
            <th className="border border-[#D1D5DB] px-4 py-2.5 text-left font-semibold">Code</th>
            <th className="border border-[#D1D5DB] px-4 py-2.5 text-center font-semibold">Qty</th>
            <th className="border border-[#D1D5DB] px-4 py-2.5 text-right font-semibold">Unit Price (₹)</th>
            <th className="border border-[#D1D5DB] px-4 py-2.5 text-right font-semibold">Total (₹)</th>
          </tr>
        </thead>
        <tbody>
          {invoice.items.map((item, index) => (
            <tr key={`${item.product_id}-${index}`}>
              <td className="border border-[#D1D5DB] px-4 py-2.5 font-medium">{item.product_name}</td>
              <td className="border border-[#D1D5DB] px-4 py-2.5 text-[#6B7280]">{item.product_code}</td>
              <td className="border border-[#D1D5DB] px-4 py-2.5 text-center">{item.quantity}</td>
              <td className="border border-[#D1D5DB] px-4 py-2.5 text-right tabular-nums">{formatINR(item.unit_price)}</td>
              <td className="border border-[#D1D5DB] px-4 py-2.5 text-right font-semibold tabular-nums">
                {formatINR(item.total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-6 flex justify-end">
        <div className="w-full max-w-xs">
          <TotalsRow label="Sub total:" value={formatINR(invoice.subtotal)} testid="invoice-sheet-subtotal" />
          {invoice.round_off !== 0 ? (
            <TotalsRow label="Round-Off:" value={formatINR(invoice.round_off)} testid="invoice-sheet-roundoff" />
          ) : null}
          {invoice.discount > 0 ? (
            <TotalsRow label="Discount:" value={`- ${formatINR(invoice.discount)}`} testid="invoice-sheet-discount" />
          ) : null}
          <div
            className="mt-2 flex items-center justify-between gap-4 rounded-md bg-[#F4EFE6] px-4 py-3"
            data-testid="invoice-sheet-total"
          >
            <span className="text-base font-extrabold tracking-wide">TOTAL:</span>
            <span className="text-lg font-extrabold tabular-nums">{formatINR(invoice.total)}</span>
          </div>
        </div>
      </div>

      <div className="mt-12 border-t border-[#E5E7EB] pt-5">
        <div className="font-invoice-serif text-lg text-[#111827]">Thank You For Your Business</div>
        <p className="mt-1 text-xs text-[#6B7280]">
          If you have any questions about this invoice. Please Contact:{" "}
          <span className="font-bold text-[#111827]">{invoice.store_phone || "-"}</span>
        </p>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FilePlus2, IndianRupee, Layers, Package, PackageCheck, Receipt, TrendingDown, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import SummaryCard from "@/components/dashboard/SummaryCard";
import InvoiceBuilderModal from "@/components/invoices/InvoiceBuilderModal";
import { fetchDashboard, fetchStockSalesReport, qk } from "@/lib/queries";
import { formatINR } from "@/lib/format";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "@/lib/recharts";
import { Search } from "lucide-react";
import type { StockSalesReportType } from "@/lib/types";

const monthFormat = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" });
const REPORT_PAGE_SIZE = 10;

function formatMonthInput(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function getMonthOptions(count = 12): string[] {
  const now = new Date();
  return Array.from({ length: count }, (_, index) => {
    const target = new Date(now.getFullYear(), now.getMonth() - index, 1);
    return formatMonthInput(target);
  });
}

export default function Dashboard() {
  const summaryQuery = useQuery({ queryKey: qk.dashboard, queryFn: fetchDashboard });
  const [selectedMonth, setSelectedMonth] = useState(() => formatMonthInput(new Date()));
  const [reportType, setReportType] = useState<StockSalesReportType>("monthly");
  const [selectedDate, setSelectedDate] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  });
  const [productSearch, setProductSearch] = useState("");
  const [productPage, setProductPage] = useState(1);
  const [builderOpen, setBuilderOpen] = useState(false);
  const summary = summaryQuery.data;
  const summaryLoading = summaryQuery.isLoading;

  const reportQuery = useQuery({
    queryKey: qk.stockSalesReport(reportType, reportType === "daily" ? selectedDate : selectedMonth),
    queryFn: () => fetchStockSalesReport(reportType, reportType === "daily" ? selectedDate : selectedMonth),
    enabled: Boolean(reportType === "daily" ? selectedDate : selectedMonth),
  });

  const monthOptions = useMemo(() => getMonthOptions(12), []);
  const report = reportQuery.data;
  const reportSummary = report?.summary;
  const filteredProducts = useMemo(() => {
    const term = productSearch.trim().toLowerCase();
    return (report?.products ?? []).filter(
      (product) =>
        !term || product.product_name.toLowerCase().includes(term) || product.product_code.toLowerCase().includes(term)
    );
  }, [report?.products, productSearch]);
  const productPageCount = Math.max(1, Math.ceil(filteredProducts.length / REPORT_PAGE_SIZE));
  const safeProductPage = Math.min(productPage, productPageCount);
  const visibleProducts = filteredProducts.slice(
    (safeProductPage - 1) * REPORT_PAGE_SIZE,
    safeProductPage * REPORT_PAGE_SIZE
  );
  const productRangeStart = filteredProducts.length === 0 ? 0 : (safeProductPage - 1) * REPORT_PAGE_SIZE + 1;
  const productRangeEnd = Math.min(safeProductPage * REPORT_PAGE_SIZE, filteredProducts.length);

  useEffect(() => {
    setProductPage(1);
  }, [productSearch, selectedMonth]);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
          <p className="mt-1 text-base text-slate-500">Stock and billing overview for your store.</p>
        </div>
        <Button size="lg" onClick={() => setBuilderOpen(true)} data-testid="dashboard-create-invoice-btn">
          <FilePlus2 className="h-5 w-5" />
          Create Invoice
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-5 md:grid-cols-3">
        <SummaryCard
          testid="metric-total-products"
          label="Total Products"
          value={summary ? summary.total_products : "-"}
          icon={Package}
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-total-stock"
          label="Total Stock"
          value={summary ? summary.total_stock : "-"}
          icon={Layers}
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-today-sales"
          label="Today's Sales"
          value={summary ? formatTodaySales(summary.today_sales) : "-"}
          icon={IndianRupee}
          tone="text-emerald-600"
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-today-invoices"
          label="Today's Invoices"
          value={summary ? summary.today_invoice_count : "-"}
          icon={Receipt}
          loading={summaryLoading}
        />
        <SummaryCard
          testid="metric-sale-count"
          label="Today's Sale Count"
          value={summary ? summary.sale_count : "-"}
          icon={PackageCheck}
          tone="text-blue-600"
          loading={summaryLoading}
        />
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <CardTitle>{reportType === "daily" ? "Daily" : "Monthly"} Stock &amp; Sales Report</CardTitle>
            <CardDescription>
              Track stock inflow, units sold, and sales value for the selected {reportType === "daily" ? "day" : "month"}.
            </CardDescription>
          </div>
          <div className="flex w-full flex-col gap-3 md:w-auto md:min-w-72">
            <div className="flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
              {(["daily", "monthly"] as const).map((type) => (
                <Button
                  key={type}
                  type="button"
                  variant={reportType === type ? "default" : "ghost"}
                  size="sm"
                  className="flex-1 capitalize"
                  onClick={() => setReportType(type)}
                  data-testid={`report-type-${type}`}
                >
                  {type}
                </Button>
              ))}
            </div>
            {reportType === "daily" ? (
              <div>
                <label htmlFor="report-date" className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Date
                </label>
                <Input id="report-date" type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} data-testid="report-date-input" />
              </div>
            ) : (
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-500">Month</label>
                <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select month" />
                  </SelectTrigger>
                  <SelectContent>
                    {monthOptions.map((month) => (
                      <SelectItem key={month} value={month}>
                        {monthFormat.format(new Date(`${month}-01T00:00:00`))}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-6 pt-0">
          {reportQuery.isLoading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 4 }).map((_, idx) => (
                <div key={idx} className="h-28 animate-pulse rounded-xl bg-slate-100" />
              ))}
            </div>
          ) : reportQuery.isError || !report ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              Could not load the {reportType} stock report for {reportType === "daily" ? selectedDate : selectedMonth}.
            </div>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <SummaryCard
                  testid="report-total-received"
                  label="Total Stock Received"
                  value={reportSummary ? reportSummary.total_stock_received : "-"}
                  icon={TrendingUp}
                  tone="text-emerald-600"
                  loading={reportQuery.isLoading}
                />
                <SummaryCard
                  testid="report-total-sold"
                  label="Total Units Sold"
                  value={reportSummary ? reportSummary.total_units_sold : "-"}
                  icon={TrendingDown}
                  tone="text-blue-600"
                  loading={reportQuery.isLoading}
                />
                <SummaryCard
                  testid="report-sales-amount"
                  label="Total Sales Amount"
                  value={reportSummary ? formatINR(reportSummary.total_sales_amount) : "-"}
                  icon={IndianRupee}
                  tone="text-violet-600"
                  loading={reportQuery.isLoading}
                />
                <SummaryCard
                  testid="report-products-sold"
                  label="Products Sold"
                  value={reportSummary ? reportSummary.products_sold : "-"}
                  icon={Package}
                  tone="text-slate-700"
                  loading={reportQuery.isLoading}
                />
              </div>

              {report.chart.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-sm text-slate-500">
                  No stock movement or sales were recorded for {reportType === "daily" ? selectedDate : monthFormat.format(new Date(`${selectedMonth}-01T00:00:00`))}.
                </div>
              ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-slate-800">Stock Received vs Sold Quantity</h3>
                  </div>
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={report.chart} barGap={8}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" vertical={false} />
                        <XAxis dataKey="product_code" tickLine={false} axisLine={false} fontSize={11} />
                        <YAxis tickLine={false} axisLine={false} allowDecimals={false} fontSize={11} />
                        <Tooltip
                          formatter={(value: number, name: string) => [value, name === "stock_received" ? "Received" : "Sold"]}
                          labelFormatter={(label) => `Product: ${label}`}
                        />
                        <Bar dataKey="stock_received" fill="#10b981" radius={[4, 4, 0, 0]} name="stock_received" />
                        <Bar dataKey="sold_quantity" fill="#3b82f6" radius={[4, 4, 0, 0]} name="sold_quantity" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              <div className="mt-3 overflow-hidden rounded-xl border border-slate-200">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-800">Product Details</h3>
                    <p className="text-xs text-slate-500">{filteredProducts.length} matching products</p>
                  </div>
                  <div className="relative w-full sm:w-72">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      value={productSearch}
                      onChange={(event) => setProductSearch(event.target.value)}
                      placeholder="Search by product name or code"
                      className="pl-9"
                      data-testid="dashboard-product-search-input"
                    />
                  </div>
                </div>
                <div className="mt-3 border-t border-slate-100 pt-3">
                  <Table className="[&_th:not(:last-child)]:border-r [&_td:not(:last-child)]:border-r [&_th:not(:last-child)]:border-slate-200 [&_td:not(:last-child)]:border-slate-200">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Product Name</TableHead>
                        <TableHead>Product Code</TableHead>
                        <TableHead>Opening Stock</TableHead>
                        <TableHead>Stock Received</TableHead>
                        <TableHead>Sold Quantity</TableHead>
                        <TableHead>Closing Stock</TableHead>
                        <TableHead>Sales Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredProducts.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} className="py-10 text-center text-sm text-slate-500">
                            {report.products.length === 0
                              ? "No product history during this month."
                              : "No products match your search."}
                          </TableCell>
                        </TableRow>
                      ) : (
                        visibleProducts.map((row) => (
                          <TableRow key={row.product_id}>
                            <TableCell className="font-medium text-slate-800">{row.product_name}</TableCell>
                            <TableCell className="font-mono text-xs text-slate-500">{row.product_code}</TableCell>
                            <TableCell>{row.opening_stock}</TableCell>
                            <TableCell>{row.stock_received}</TableCell>
                            <TableCell>{row.sold_quantity}</TableCell>
                            <TableCell>{row.closing_stock}</TableCell>
                            <TableCell className="font-medium tabular-nums text-slate-700">{formatINR(row.sales_amount)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3">
                  <span className="text-xs text-slate-500" data-testid="dashboard-product-pagination-range">
                    Showing {productRangeStart}-{productRangeEnd} of {filteredProducts.length} products
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={safeProductPage <= 1}
                      onClick={() => setProductPage(safeProductPage - 1)}
                      data-testid="dashboard-product-pagination-prev"
                    >
                      Previous
                    </Button>
                    <span className="text-xs font-medium text-slate-600" data-testid="dashboard-product-pagination-info">
                      Page {safeProductPage} of {productPageCount}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={safeProductPage >= productPageCount}
                      onClick={() => setProductPage(safeProductPage + 1)}
                      data-testid="dashboard-product-pagination-next"
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </div>

              {report.note ? <p className="text-xs text-slate-500">{report.note}</p> : null}
            </>
          )}
        </CardContent>
      </Card>

      <InvoiceBuilderModal open={builderOpen} onOpenChange={setBuilderOpen} />
    </div>
  );
}

function formatTodaySales(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

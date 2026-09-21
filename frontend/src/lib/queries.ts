import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/lib/api";
import type {
  DashboardSummary,
  Invoice,
  InvoiceCreate,
  InvoiceListResponse,
  MonthlyStockSalesReport,
  NextInvoiceNumber,
  Product,
  ProductCreate,
  ProductUpdate,
  StoreSettings,
  StoreSettingsUpdate,
  StockSalesReportType,
} from "@/lib/types";

export interface InvoiceFilters {
  search?: string;
  date_from?: string;
  date_to?: string;
}

export interface InvoicePage {
  page?: number;
  limit?: number;
}

export const qk = {
  products: ["products"] as const,
  dashboard: ["dashboard"] as const,
  settings: ["settings"] as const,
  nextInvoiceNumber: ["invoices", "next-number"] as const,
  invoices: (filters: InvoiceFilters, page = 1, limit = 10) => ["invoices", "list", filters, page, limit] as const,
  invoice: (id: string) => ["invoices", "detail", id] as const,
  stockSalesReport: (type: StockSalesReportType, value: string) => ["reports", "stock-sales", type, value] as const,
};

function toQueryString(filters: InvoiceFilters, page: InvoicePage = {}): string {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (page.page !== undefined) params.set("page", String(page.page));
  if (page.limit !== undefined) params.set("limit", String(page.limit));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const fetchProducts = () => apiGet<Product[]>("/products");
export const fetchDashboard = () => apiGet<DashboardSummary>("/dashboard");
export const fetchStockSalesReport = (type: StockSalesReportType, value: string) =>
  apiGet<MonthlyStockSalesReport>(
    `/reports/stock-sales?${type === "daily" ? "date" : "month"}=${encodeURIComponent(value)}`
  );
export const fetchSettings = () => apiGet<StoreSettings>("/settings");
export const fetchNextInvoiceNumber = () => apiGet<NextInvoiceNumber>("/invoices/next-number");
export const fetchInvoices = (filters: InvoiceFilters, page: InvoicePage = {}) =>
  apiGet<InvoiceListResponse>(`/invoices${toQueryString(filters, page)}`);

export const createProduct = (body: ProductCreate) => apiPost<Product>("/products", body);
export const updateProduct = (id: string, body: ProductUpdate) => apiPut<Product>(`/products/${id}`, body);
export const addStock = (id: string, additionalQuantity: number) =>
  apiPatch<Product>(`/products/${id}/stock`, { additional_quantity: additionalQuantity });
export const deleteProduct = (id: string) => apiDelete<void>(`/products/${id}`);
export const createInvoice = (body: InvoiceCreate) => apiPost<Invoice>("/invoices", body);
export const deleteInvoice = (id: string) => apiDelete<void>(`/invoices/${id}`);
export const updateSettings = (body: StoreSettingsUpdate) => apiPut<StoreSettings>("/settings", body);

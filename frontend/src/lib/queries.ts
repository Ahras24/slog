import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/lib/api";
import type {
  DashboardSummary,
  Invoice,
  InvoiceCreate,
  NextInvoiceNumber,
  Product,
  ProductCreate,
  ProductUpdate,
  StoreSettings,
  StoreSettingsUpdate,
} from "@/lib/types";

export interface InvoiceFilters {
  search?: string;
  date_from?: string;
  date_to?: string;
}

export const qk = {
  products: ["products"] as const,
  dashboard: ["dashboard"] as const,
  settings: ["settings"] as const,
  nextInvoiceNumber: ["invoices", "next-number"] as const,
  invoices: (filters: InvoiceFilters) => ["invoices", "list", filters] as const,
  invoice: (id: string) => ["invoices", "detail", id] as const,
};

function toQueryString(filters: InvoiceFilters): string {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const fetchProducts = () => apiGet<Product[]>("/products");
export const fetchDashboard = () => apiGet<DashboardSummary>("/dashboard");
export const fetchSettings = () => apiGet<StoreSettings>("/settings");
export const fetchNextInvoiceNumber = () => apiGet<NextInvoiceNumber>("/invoices/next-number");
export const fetchInvoices = (filters: InvoiceFilters) => apiGet<Invoice[]>(`/invoices${toQueryString(filters)}`);

export const createProduct = (body: ProductCreate) => apiPost<Product>("/products", body);
export const updateProduct = (id: string, body: ProductUpdate) => apiPut<Product>(`/products/${id}`, body);
export const addStock = (id: string, additionalQuantity: number) =>
  apiPatch<Product>(`/products/${id}/stock`, { additional_quantity: additionalQuantity });
export const deleteProduct = (id: string) => apiDelete<void>(`/products/${id}`);
export const createInvoice = (body: InvoiceCreate) => apiPost<Invoice>("/invoices", body);
export const updateSettings = (body: StoreSettingsUpdate) => apiPut<StoreSettings>("/settings", body);

// Hand-written mirrors of the backend Pydantic models (backend/models/*) — keep both in sync in the same edit.

export type StockStatus = "in_stock" | "low_stock" | "out_of_stock";

export type StockFilter = "all" | StockStatus;

export interface Product {
  id: string;
  name: string;
  code: string;
  stock: number;
  unit_price: number;
  status: StockStatus;
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  name: string;
  code: string;
  stock: number;
  unit_price: number;
}

export interface ProductUpdate {
  name?: string;
  code?: string;
  stock?: number;
  unit_price?: number;
}

export interface InvoiceItem {
  product_id: string;
  product_name: string;
  product_code: string;
  quantity: number;
  unit_price: number;
  total: number;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  date: string;
  customer_name: string;
  company_name: string;
  street_address: string;
  city_pincode: string;
  phone: string;
  email: string;
  items: InvoiceItem[];
  subtotal: number;
  discount: number;
  round_off: number;
  total: number;
  status: string;
  store_phone: string;
  created_at: string;
}

export interface InvoiceCreateItem {
  product_id: string;
  quantity: number;
}

export interface InvoiceCreate {
  customer_name: string;
  company_name: string;
  street_address: string;
  city_pincode: string;
  phone: string;
  email: string;
  date?: string;
  discount: number;
  items: InvoiceCreateItem[];
}

export interface NextInvoiceNumber {
  invoice_number: string;
  date: string;
}

export interface DashboardSummary {
  total_products: number;
  total_stock: number;
  low_stock: number;
  out_of_stock: number;
  today_sales: number;
  today_invoice_count: number;
}

export interface StoreSettings {
  store_name: string;
  phone: string;
  email: string;
  street_address: string;
  city_pincode: string;
  updated_at: string;
}

export interface StoreSettingsUpdate {
  store_name: string;
  phone: string;
  email: string;
  street_address: string;
  city_pincode: string;
}

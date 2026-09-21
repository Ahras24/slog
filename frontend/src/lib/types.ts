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

export type PaymentMethod = "Cash(S)" | "Cash(A)" | "Cash(I)" | "Cash(Z)" | "Cash";

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
  payment_method?: PaymentMethod;
  items: InvoiceItem[];
  subtotal: number;
  discount: number;
  round_off: number;
  total: number;
  status: string;
  store_phone: string;
  created_at: string;
}

export interface InvoiceListResponse {
  invoices: Invoice[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
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
  payment_method: PaymentMethod;
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
  sale_count: number;
}

export interface StockSalesSummary {
  total_stock_received: number;
  total_units_sold: number;
  total_sales_amount: number;
  products_sold: number;
}

export interface StockSalesProductRow {
  product_id: string;
  product_name: string;
  product_code: string;
  opening_stock: number;
  stock_received: number;
  sold_quantity: number;
  closing_stock: number;
  sales_amount: number;
}

export interface StockSalesChartPoint {
  product_name: string;
  product_code: string;
  stock_received: number;
  sold_quantity: number;
  sales_amount: number;
}

export type StockSalesReportType = "daily" | "monthly";

export interface MonthlyStockSalesReport {
  selected_month: string;
  selected_date?: string | null;
  report_type?: StockSalesReportType;
  summary: StockSalesSummary;
  products: StockSalesProductRow[];
  chart: StockSalesChartPoint[];
  note?: string | null;
}

export interface StoreSettings {
  store_name: string;
  phone: string;
  email: string;
  street_address: string;
  city_pincode: string;
  invoice_prefix: string;
  updated_at: string;
}

export interface StoreSettingsUpdate {
  store_name: string;
  phone: string;
  email: string;
  street_address: string;
  city_pincode: string;
  invoice_prefix: string;
}

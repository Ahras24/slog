import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FilePlus2, History, LayoutDashboard, Menu, Package, Settings, Store } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { fetchSettings, qk } from "@/lib/queries";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard", end: true },
  { to: "/products", label: "Products & Stock", icon: Package, testid: "nav-products", end: false },
  { to: "/invoices/new", label: "Create Invoice", icon: FilePlus2, testid: "nav-create-invoice", end: false },
  { to: "/invoices", label: "Invoice History", icon: History, testid: "nav-invoices-history", end: true },
  { to: "/settings", label: "Settings", icon: Settings, testid: "nav-settings", end: false },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-1 px-3">
      {NAV_ITEMS.map(({ to, label, icon: Icon, testid, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150",
              isActive
                ? "bg-slate-100 text-[#0F2942]"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            )
          }
          data-testid={testid}
        >
          <Icon className="h-4 w-4" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

function Brand({ storeName }: { storeName?: string }) {
  return (
    <div className="flex items-center gap-3 px-6 pb-4 pt-6">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#0F2942] text-white">
        <Store className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-slate-900" data-testid="sidebar-store-name">
          {storeName ?? "Store Admin"}
        </div>
        <div className="text-xs text-slate-500">Stock &amp; Billing</div>
      </div>
    </div>
  );
}

function ProfileMenu({ storeName }: { storeName?: string }) {
  const initials = (storeName ?? "AD")
    .split(/\s+/)
    .map((word) => word[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-xs font-semibold text-[#0F2942] shadow-sm transition-colors duration-150 hover:bg-slate-50"
        data-testid="profile-menu-button"
      >
        {initials}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="text-sm font-medium text-slate-900">{storeName ?? "Store Admin"}</div>
          <div className="text-xs font-normal text-slate-500">Admin Panel</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem render={<Link to="/settings" />} data-testid="profile-settings-item">
          <Settings className="h-4 w-4" />
          Store Settings
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const { data: settings } = useQuery({ queryKey: qk.settings, queryFn: fetchSettings, retry: false });

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-svh bg-[#F8FAFC]">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-slate-200 bg-white lg:flex">
        <Brand storeName={settings?.store_name} />
        <NavLinks />
        <div className="mt-auto px-6 py-4 text-xs text-slate-400">Internal store panel</div>
      </aside>

      <div className="flex min-h-svh flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 transition-colors hover:bg-slate-50 lg:hidden"
              data-testid="mobile-menu-button"
            >
              <Menu className="h-4 w-4" />
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <SheetHeader className="border-b border-slate-200">
                <SheetTitle className="text-left text-sm font-semibold text-slate-900">
                  {settings?.store_name ?? "Store Admin"}
                </SheetTitle>
              </SheetHeader>
              <div className="py-3">
                <NavLinks onNavigate={() => setMobileOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>
          <div className="flex-1" />
          <ProfileMenu storeName={settings?.store_name} />
        </header>
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl animate-in fade-in duration-200">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

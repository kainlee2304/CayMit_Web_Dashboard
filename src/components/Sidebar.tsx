"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart2,
  Boxes,
  History,
  LayoutDashboard,
  Sprout,
  LogOut,
  Menu,
  QrCode,
  Settings,
  Video,
  X,
  Users,
  ShieldCheck,
  Building2,
  Map,
  CalendarRange,
  BookOpen,
} from "lucide-react";
import { useAuth, ROLE_LABELS } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", closeOnEscape);
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [open]);

  // Define navigation items with translation keys & allowed roles
  const navItems = [
    {
      href: "/",
      label: t.nav.dashboard,
      icon: LayoutDashboard,
      roles: ["admin_hq", "admin", "farmer", "producer", "technician", "processor", "packhouse_lead", "qa_qc", "logistics"],
    },
    {
      href: "/farmers",
      label: t.nav.farmers,
      icon: Users,
      roles: ["admin_hq", "admin"], // Only HQ Admin manages farmer accounts
    },
    {
      href: "/growing-areas",
      label: t.nav.growingAreas,
      icon: ShieldCheck,
      roles: ["admin_hq", "admin", "technician"], // Admin & Technician manage/inspect PUCs
    },
    {
      href: "/farms",
      label: user?.role === "farmer" || user?.role === "producer" ? t.dashboard.myFarms : t.nav.farms,
      icon: Building2,
      roles: ["admin_hq", "admin", "farmer", "producer", "technician"],
    },
    {
      href: "/seasons",
      label: t.nav.seasons,
      icon: CalendarRange,
      roles: ["admin_hq", "admin", "farmer", "producer", "technician"],
    },
    {
      href: "/farm-diary",
      label: t.nav.farmDiary,
      icon: BookOpen,
      roles: ["admin_hq", "admin", "farmer", "producer", "technician"],
    },
    {
      href: "/map",
      label: t.nav.map,
      icon: Map,
      roles: ["admin_hq", "admin", "farmer", "producer", "technician", "logistics"],
    },
    {
      href: "/live",
      label: t.nav.live,
      icon: Video,
      roles: ["admin_hq", "admin", "farmer", "producer"],
    },
    {
      href: "/history",
      label: t.nav.history,
      icon: History,
      roles: ["admin_hq", "admin", "farmer", "producer", "technician", "processor", "packhouse_lead", "qa_qc"],
    },
    {
      href: "/stats",
      label: t.nav.stats,
      icon: BarChart2,
      roles: ["admin_hq", "admin", "packhouse_lead", "qa_qc", "processor"],
    },
    {
      href: "/batches",
      label: t.nav.batches,
      icon: Boxes,
      roles: ["admin_hq", "admin", "packhouse_lead", "processor", "logistics"],
    },
    {
      href: "/trace",
      label: t.nav.trace,
      icon: QrCode,
      roles: ["admin_hq", "admin", "farmer", "producer", "technician", "packhouse_lead", "processor", "logistics"],
    },
  ];

  // Helper to check active state strictly
  const isNavActive = (href: string) => {
    if (href === "/") {
      return pathname === "/" || pathname === "";
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const Brand = () => (
    <div className="flex min-w-0 items-center gap-3">
      <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-emerald-500 shadow-lg shadow-emerald-500/20">
        <Sprout className="h-6 w-6 text-white" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-black text-white">{t.brand.name}</p>
        <p className="truncate text-[11px] font-medium text-emerald-400">{t.brand.subtitle}</p>
      </div>
    </div>
  );

  const userRoleKey = (user?.role as keyof typeof t.roles) || "farmer";

  return (
    <>
      {/* Mobile Top Header */}
      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-gray-800 bg-gray-900/95 px-4 backdrop-blur lg:hidden">
        <Brand />
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-gray-700 bg-gray-800 text-gray-200"
          aria-label="Mở menu điều hướng"
          aria-expanded={open}
        >
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {open && (
        <button
          type="button"
          aria-label="Đóng menu"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Main Sidebar Desktop / Drawer Mobile */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[min(20rem,86vw)] flex-col border-r border-gray-800 bg-gray-900 shadow-2xl transition-transform duration-200 lg:static lg:z-auto lg:w-64 lg:flex-shrink-0 lg:translate-x-0 lg:shadow-none font-sans ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-20 items-center justify-between border-b border-gray-800 px-5 lg:h-auto lg:px-6 lg:py-5">
          <Brand />
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="flex h-10 w-10 items-center justify-center rounded-xl text-gray-400 hover:bg-gray-800 hover:text-white lg:hidden"
            aria-label="Đóng menu điều hướng"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Items Filtered by Role */}
        <nav className="flex-1 space-y-1.5 overflow-y-auto px-3 py-4">
          {navItems
            .filter((item) => !user || item.roles.includes(user.role))
            .map(({ href, label, icon: Icon }) => {
              const active = isNavActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setOpen(false)}
                  className={`flex min-h-11 items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all ${
                    active
                      ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-400 shadow-sm"
                      : "text-gray-400 hover:bg-gray-800/80 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  <span className="truncate">{label}</span>
                </Link>
              );
            })}

          {/* Admin Specific Settings Menu */}
          {(user?.role === "admin" || user?.role === "admin_hq") && (
            <Link
              href="/admin"
              onClick={() => setOpen(false)}
              className={`flex min-h-11 items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all ${
                isNavActive("/admin")
                  ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-400 shadow-sm"
                  : "text-gray-400 hover:bg-gray-800/80 hover:text-white"
              }`}
            >
              <Settings className="h-4 w-4" />
              <span>{t.nav.admin}</span>
            </Link>
          )}
        </nav>

        {/* User Card & Logout in Footer */}
        <div className="border-t border-gray-800 px-4 py-4">
          {user && (
            <div className="mb-3 rounded-2xl bg-gray-950/70 p-3 border border-gray-800/60">
              <p className="truncate text-xs font-bold text-white">{user.display_name}</p>
              <p className="truncate text-[11px] text-emerald-400 font-medium">
                {t.roles[userRoleKey] || ROLE_LABELS[user.role] || user.role}
              </p>
              <p className="mt-0.5 truncate text-[10px] text-gray-500">{user.organization}</p>
            </div>
          )}
          {user && (
            <button
              type="button"
              onClick={() => {
                logout();
                window.location.href = "/login";
              }}
              className="flex min-h-10 w-full items-center justify-center gap-2 rounded-xl border border-gray-700 text-xs font-semibold text-gray-300 hover:bg-gray-800 hover:text-rose-400 transition"
            >
              <LogOut className="h-3.5 w-3.5" />
              {t.nav.logout}
            </button>
          )}
        </div>
      </aside>
    </>
  );
}

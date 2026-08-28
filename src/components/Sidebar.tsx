"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Boxes, History, LayoutDashboard, Leaf, LogOut, Menu, QrCode, Settings, Video, X } from "lucide-react";
import { ROLE_LABELS, useAuth } from "@/context/AuthContext";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, roles:["admin","producer","processor"] },
  { href: "/live", label: "Camera Live", icon: Video, roles:["admin","producer"] },
  { href: "/history", label: "Lịch Sử AI", icon: History, roles:["admin","producer","processor"] },
  { href: "/stats", label: "Thống Kê", icon: BarChart2, roles:["admin","producer","processor"] },
  { href: "/batches", label: "Quản Lý Lô", icon: Boxes, roles:["admin","producer","processor","logistics"] },
  { href: "/trace", label: "Truy Xuất QR", icon: QrCode, roles:["admin","producer","processor","logistics"] },
];

function Brand() {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-emerald-500">
        <Leaf className="h-5 w-5 text-white" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-white">CayMit AI</p>
        <p className="truncate text-xs text-gray-500">Disease Detection</p>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
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

  return (
    <>
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

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[min(20rem,86vw)] flex-col border-r border-gray-800 bg-gray-900 shadow-2xl transition-transform duration-200 lg:static lg:z-auto lg:w-60 lg:flex-shrink-0 lg:translate-x-0 lg:shadow-none ${
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

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.filter(item=>!!user&&item.roles.includes(user.role)).map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={`flex min-h-12 items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all ${
                  active
                    ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-400"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                {label}
              </Link>
            );
          })}
          {user?.role==="admin"&&<Link href="/admin" onClick={()=>setOpen(false)} className={`flex min-h-12 items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium ${pathname==="/admin"?"border border-emerald-500/30 bg-emerald-500/20 text-emerald-400":"text-gray-400 hover:bg-gray-800 hover:text-white"}`}><Settings className="h-5 w-5"/>Quản trị</Link>}
        </nav>

        <div className="border-t border-gray-800 px-4 py-4">
          {user&&<div className="mb-3 rounded-xl bg-gray-950/60 p-3"><p className="truncate text-sm font-bold text-white">{user.display_name}</p><p className="truncate text-xs text-emerald-400">{ROLE_LABELS[user.role]}</p><p className="mt-0.5 truncate text-xs text-gray-500">{user.organization}</p></div>}
          {user&&<button onClick={()=>{logout();window.location.href="/login"}} className="flex min-h-10 w-full items-center justify-center gap-2 rounded-xl border border-gray-700 text-sm font-semibold text-gray-300 hover:bg-gray-800"><LogOut className="h-4 w-4"/>Đăng xuất</button>}
        </div>
      </aside>
    </>
  );
}

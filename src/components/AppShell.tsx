"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import AutoCaptureToast from "@/components/AutoCaptureToast";
import { useAuth } from "@/context/AuthContext";

const PUBLIC_PATHS = ["/login", "/register", "/trace"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  const normalizedPath = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const isAuth = normalizedPath === "/login" || normalizedPath === "/register";
  const isPublic = PUBLIC_PATHS.includes(normalizedPath);

  useEffect(() => {
    if (!loading && !user && !isPublic) {
      router.replace(`/login/?next=${encodeURIComponent(normalizedPath)}`);
    }
    if (!loading && user && isAuth) {
      router.replace("/");
    }
  }, [loading, user, isPublic, isAuth, normalizedPath, router]);

  if (loading || (!user && !isPublic) || (user && isAuth)) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-gray-950 text-gray-400 font-sans">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
          <span>Đang kiểm tra phiên đăng nhập…</span>
        </div>
      </div>
    );
  }

  if (isAuth) {
    return <>{children}</>;
  }

  return (
    <>
      <div className="flex min-h-dvh min-w-0 flex-col lg:h-dvh lg:flex-row lg:overflow-hidden font-sans">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="min-w-0 flex-1 overflow-x-hidden px-4 py-5 sm:p-6 lg:overflow-y-auto bg-gray-950">
            {children}
          </main>
        </div>
      </div>
      {user && <AutoCaptureToast />}
    </>
  );
}

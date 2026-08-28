"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import AutoCaptureToast from "@/components/AutoCaptureToast";
import { useAuth } from "@/context/AuthContext";

const PUBLIC_PATHS=["/login","/register","/trace"];
export default function AppShell({children}:{children:React.ReactNode}){
  const pathname=usePathname();const router=useRouter();const{user,loading}=useAuth();
  const normalizedPath=pathname.length>1?pathname.replace(/\/+$/,""):pathname;
  const isAuth=normalizedPath==="/login"||normalizedPath==="/register";const isPublic=PUBLIC_PATHS.includes(normalizedPath);
  useEffect(()=>{if(!loading&&!user&&!isPublic)router.replace(`/login/?next=${encodeURIComponent(normalizedPath)}`);if(!loading&&user&&isAuth)router.replace("/")},[loading,user,isPublic,isAuth,normalizedPath,router]);
  if(loading||(!user&&!isPublic)||(user&&isAuth))return <div className="flex min-h-dvh items-center justify-center bg-gray-950 text-gray-400">Đang kiểm tra phiên đăng nhập…</div>;
  if(isAuth)return <>{children}</>;
  return <><div className="flex min-h-dvh min-w-0 flex-col lg:h-dvh lg:flex-row lg:overflow-hidden"><Sidebar/><main className="min-w-0 flex-1 overflow-x-hidden px-3 py-4 sm:p-6 lg:overflow-y-auto">{children}</main></div>{user&&<AutoCaptureToast/>}</>;
}

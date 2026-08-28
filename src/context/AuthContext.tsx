"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getTraceMe, loginTrace, registerTrace, TraceAuth, TraceRole, TraceUser } from "@/lib/api";

const TOKEN_KEY = "caymit_access_token";
type RegisterData = { username:string; password:string; display_name:string; organization:string; role:Exclude<TraceRole,"admin"> };
type AuthValue = { user:TraceUser|null; token:string; loading:boolean; login:(username:string,password:string)=>Promise<void>; register:(data:RegisterData)=>Promise<string>; logout:()=>void };
const AuthContext = createContext<AuthValue|null>(null);

export function AuthProvider({children}:{children:React.ReactNode}) {
  const [user,setUser]=useState<TraceUser|null>(null); const [token,setToken]=useState(""); const [loading,setLoading]=useState(true);
  const accept=(auth:TraceAuth)=>{localStorage.setItem(TOKEN_KEY,auth.access_token);localStorage.setItem("trace_token",auth.access_token);setToken(auth.access_token);setUser(auth.user)};
  useEffect(()=>{void(async()=>{const saved=localStorage.getItem(TOKEN_KEY)||localStorage.getItem("trace_token");if(!saved)return;try{const me=await getTraceMe(saved);setToken(saved);setUser(me);localStorage.setItem(TOKEN_KEY,saved)}catch{localStorage.removeItem(TOKEN_KEY);localStorage.removeItem("trace_token")}})().finally(()=>setLoading(false))},[]);
  const value=useMemo<AuthValue>(()=>({user,token,loading,login:async(username,password)=>accept(await loginTrace({username,password})),register:async(data)=>(await registerTrace(data)).message,logout:()=>{localStorage.removeItem(TOKEN_KEY);localStorage.removeItem("trace_token");setToken("");setUser(null)}}),[user,token,loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error("useAuth must be used inside AuthProvider");return value}
export const ROLE_LABELS:Record<TraceRole,string>={admin:"Quản trị viên",producer:"Nông hộ / HTX",processor:"Sơ chế / Đóng gói",logistics:"Logistics / Xuất khẩu"};

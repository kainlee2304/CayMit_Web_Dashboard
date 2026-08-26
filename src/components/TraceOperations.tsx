"use client";

import { FormEvent, useEffect, useState } from "react";
import { LogIn, LogOut, PackagePlus, Plus, Shield, UserPlus, Users } from "lucide-react";
import {
  appendTraceEvent, bootstrapTraceAdmin, createTraceBatch, createTraceUser,
  getTraceAuthStatus, getTraceBatches, getTraceMe, getTraceUsers, loginTrace,
  TraceBatch, TraceRole, TraceUser,
} from "@/lib/api";

const ROLE_LABELS: Record<TraceRole,string> = {admin:"Quản trị",producer:"Nông hộ / HTX",processor:"Sơ chế / Đóng gói",logistics:"Logistics / Xuất khẩu"};
const ROLE_STAGES: Record<TraceRole,Array<[string,string]>> = {
  admin:[["cultivation","Canh tác"],["harvest","Thu hoạch"],["processing","Sơ chế"],["packing","Đóng gói"],["cold_storage","Kho lạnh"],["logistics","Vận chuyển"],["export","Xuất khẩu"],["market","Thị trường"]],
  producer:[["cultivation","Canh tác"],["harvest","Thu hoạch"]],
  processor:[["processing","Sơ chế"],["packing","Đóng gói"],["cold_storage","Kho lạnh"]],
  logistics:[["logistics","Vận chuyển"],["export","Xuất khẩu"],["market","Thị trường"]],
};

export default function TraceOperations({onBatch}:{onBatch:(batch:TraceBatch)=>void}) {
  const[initialized,setInitialized]=useState<boolean|null>(null);const[token,setToken]=useState("");const[user,setUser]=useState<TraceUser|null>(null);
  const[error,setError]=useState("");const[busy,setBusy]=useState(false);const[batches,setBatches]=useState<TraceBatch[]>([]);const[selected,setSelected]=useState<TraceBatch|null>(null);const[users,setUsers]=useState<TraceUser[]>([]);
  const[auth,setAuth]=useState({username:"",password:"",display_name:"",organization:""});
  const[lot,setLot]=useState({product_name:"Mít tươi",variety:"Mít Thái",farm_name:"",origin:"",harvest_date:""});
  const[account,setAccount]=useState({username:"",password:"",display_name:"",organization:"",role:"producer" as TraceRole});
  const[event,setEvent]=useState({stage:"",title:"",location:"",details:""});

  const loadData=async(activeToken:string,activeUser:TraceUser)=>{const list=await getTraceBatches();setBatches(list);if(activeUser.role==="admin")setUsers(await getTraceUsers(activeToken));};
  useEffect(()=>{void(async()=>{const status=await getTraceAuthStatus();setInitialized(status.initialized);const saved=localStorage.getItem("trace_token");if(saved){try{const me=await getTraceMe(saved);setToken(saved);setUser(me);await loadData(saved,me)}catch{localStorage.removeItem("trace_token")}}})()},[]);
  useEffect(()=>{if(user&&!event.stage)setEvent(x=>({...x,stage:ROLE_STAGES[user.role][0]?.[0]||""}))},[user,event.stage]);

  const run=async(action:()=>Promise<void>)=>{setBusy(true);setError("");try{await action()}catch(e:any){setError(e?.response?.data?.detail||"Không thực hiện được thao tác") }finally{setBusy(false)}};
  const authenticate=(response:{access_token:string;user:TraceUser})=>{localStorage.setItem("trace_token",response.access_token);setToken(response.access_token);setUser(response.user);setInitialized(true);return loadData(response.access_token,response.user)};
  const submitAuth=(e:FormEvent)=>{e.preventDefault();void run(async()=>{const response=initialized?await loginTrace({username:auth.username,password:auth.password}):await bootstrapTraceAdmin(auth);await authenticate(response)})};
  const logout=()=>{localStorage.removeItem("trace_token");setToken("");setUser(null);setBatches([]);setSelected(null)};

  if(initialized===null)return <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5 text-sm text-gray-400">Đang kiểm tra quyền vận hành…</div>;
  if(!user)return <section className="rounded-3xl border border-amber-500/25 bg-gray-900 p-5 sm:p-7"><div className="flex items-start gap-3"><div className="rounded-xl bg-amber-500/15 p-2.5"><LogIn className="h-5 w-5 text-amber-400"/></div><div><h2 className="text-xl font-black text-white">{initialized?"Đăng nhập đơn vị vận hành":"Khởi tạo tài khoản quản trị"}</h2><p className="mt-1 text-sm text-gray-400">{initialized?"Tài khoản quyết định công đoạn được phép ghi vào chuỗi.":"Hệ thống chưa có người dùng. Tài khoản đầu tiên sẽ là quản trị viên."}</p></div></div><form onSubmit={submitAuth} className="mt-5 grid gap-3 sm:grid-cols-2">{!initialized&&<><Input label="Họ tên quản trị" value={auth.display_name} set={v=>setAuth({...auth,display_name:v})}/><Input label="Đơn vị" value={auth.organization} set={v=>setAuth({...auth,organization:v})}/></>}<Input label="Tên đăng nhập" value={auth.username} set={v=>setAuth({...auth,username:v})}/><Input label="Mật khẩu (tối thiểu 8 ký tự)" type="password" value={auth.password} set={v=>setAuth({...auth,password:v})}/>{error&&<p className="text-sm text-red-400 sm:col-span-2">{error}</p>}<button disabled={busy} className="min-h-12 rounded-xl bg-amber-500 px-5 font-bold text-gray-950 disabled:opacity-50 sm:col-span-2">{busy?"Đang xử lý…":initialized?"Đăng nhập":"Tạo quản trị viên đầu tiên"}</button></form></section>;

  const canCreate=user.role==="admin"||user.role==="producer";
  return <section className="space-y-4 rounded-3xl border border-emerald-500/25 bg-gray-900 p-5 sm:p-7">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><div className="rounded-xl bg-emerald-500/15 p-2.5"><Shield className="h-5 w-5 text-emerald-400"/></div><div><h2 className="font-black text-white">{user.display_name} · {user.organization}</h2><p className="text-sm font-semibold text-emerald-400">{ROLE_LABELS[user.role]}</p></div></div><button onClick={logout} className="flex min-h-10 items-center justify-center gap-2 rounded-xl border border-gray-700 px-4 text-sm font-bold text-gray-300"><LogOut className="h-4 w-4"/>Đăng xuất</button></div>
    <div className="rounded-xl border border-gray-800 bg-gray-950/50 p-3 text-sm text-gray-400"><strong className="text-gray-200">Quyền ghi:</strong> {user.role==="admin"?"Tất cả công đoạn":ROLE_STAGES[user.role].map(x=>x[1]).join(", ")}{canCreate&&" · Tạo lô mới"}</div>
    {error&&<p className="rounded-xl bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

    <div className="grid gap-4 xl:grid-cols-2">
      {canCreate&&<Panel icon={PackagePlus} title="Tạo lô nông sản"><form onSubmit={e=>{e.preventDefault();void run(async()=>{const created=await createTraceBatch(token,lot);setSelected(created);onBatch(created);setBatches(await getTraceBatches())})}} className="grid gap-3 sm:grid-cols-2"><Input label="Sản phẩm" value={lot.product_name} set={v=>setLot({...lot,product_name:v})}/><Input label="Giống" value={lot.variety} set={v=>setLot({...lot,variety:v})}/><Input label="Cơ sở / vườn" value={lot.farm_name} set={v=>setLot({...lot,farm_name:v})}/><Input label="Vùng trồng" value={lot.origin} set={v=>setLot({...lot,origin:v})}/><Input label="Ngày thu hoạch" type="date" value={lot.harvest_date} set={v=>setLot({...lot,harvest_date:v})}/><button disabled={busy} className="min-h-11 self-end rounded-xl bg-emerald-500 px-4 font-bold text-white disabled:opacity-50"><Plus className="mr-1 inline h-4 w-4"/>Tạo lô & QR</button></form></Panel>}
      {user.role==="admin"&&<Panel icon={UserPlus} title="Cấp tài khoản theo vai trò"><form onSubmit={e=>{e.preventDefault();void run(async()=>{await createTraceUser(token,account);setUsers(await getTraceUsers(token));setAccount({...account,username:"",password:"",display_name:"",organization:""})})}} className="grid gap-3 sm:grid-cols-2"><Input label="Họ tên" value={account.display_name} set={v=>setAccount({...account,display_name:v})}/><Input label="Đơn vị" value={account.organization} set={v=>setAccount({...account,organization:v})}/><Input label="Tên đăng nhập" value={account.username} set={v=>setAccount({...account,username:v})}/><Input label="Mật khẩu" type="password" value={account.password} set={v=>setAccount({...account,password:v})}/><label className="text-xs font-bold text-gray-400">Vai trò<select value={account.role} onChange={e=>setAccount({...account,role:e.target.value as TraceRole})} className="mt-1.5 min-h-11 w-full rounded-xl border border-gray-700 bg-gray-950 px-3 text-sm text-white"><option value="producer">Nông hộ / HTX</option><option value="processor">Sơ chế / Đóng gói</option><option value="logistics">Logistics / Xuất khẩu</option></select></label><button disabled={busy} className="min-h-11 self-end rounded-xl bg-blue-500 px-4 font-bold text-white disabled:opacity-50">Cấp tài khoản</button></form>{users.length>0&&<div className="mt-4 flex flex-wrap gap-2">{users.map(x=><span key={x.id} className="rounded-full border border-gray-700 px-3 py-1.5 text-xs text-gray-300">{x.display_name} · {ROLE_LABELS[x.role]}</span>)}</div>}</Panel>}
    </div>

    <Panel icon={Users} title="Chọn lô để cập nhật công đoạn"><div className="flex gap-2 overflow-x-auto pb-2">{batches.map(x=><button key={x.trace_code} onClick={()=>{setSelected(x);onBatch(x)}} className={`min-w-52 rounded-xl border p-3 text-left ${selected?.trace_code===x.trace_code?"border-emerald-400 bg-emerald-500/10":"border-gray-700 bg-gray-950"}`}><strong className="block text-sm text-white">{x.product_name}</strong><span className="mt-1 block font-mono text-xs text-emerald-400">{x.trace_code}</span><span className="mt-1 block text-xs text-gray-500">{x.events.length} khối · {x.origin}</span></button>)}</div>
      {selected&&<form onSubmit={e=>{e.preventDefault();void run(async()=>{const updated=await appendTraceEvent(token,selected.trace_code,event);setSelected(updated);onBatch(updated);setBatches(await getTraceBatches())})}} className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-xs font-bold text-gray-400">Công đoạn<select value={event.stage} onChange={e=>setEvent({...event,stage:e.target.value})} className="mt-1.5 min-h-11 w-full rounded-xl border border-gray-700 bg-gray-950 px-3 text-sm text-white">{ROLE_STAGES[user.role].map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label><Input label="Nội dung" value={event.title} set={v=>setEvent({...event,title:v})}/><Input label="Địa điểm" value={event.location} set={v=>setEvent({...event,location:v})}/><Input label="Ghi chú / chứng nhận" value={event.details} set={v=>setEvent({...event,details:v})}/><button disabled={busy||!event.title} className="min-h-11 rounded-xl bg-emerald-500 px-4 font-bold text-white disabled:opacity-50 sm:col-span-2">Ghi công đoạn bằng danh tính {user.organization}</button></form>}
    </Panel>
  </section>;
}

function Panel({icon:Icon,title,children}:{icon:typeof Users;title:string;children:React.ReactNode}){return <div className="rounded-2xl border border-gray-800 bg-gray-950/45 p-4"><h3 className="mb-4 flex items-center gap-2 font-black text-white"><Icon className="h-5 w-5 text-emerald-400"/>{title}</h3>{children}</div>}
function Input({label,value,set,type="text"}:{label:string;value:string;set:(value:string)=>void;type?:string}){return <label className="text-xs font-bold text-gray-400">{label}<input required type={type} value={value} onChange={e=>set(e.target.value)} className="mt-1.5 min-h-11 w-full rounded-xl border border-gray-700 bg-gray-950 px-3 text-sm text-white outline-none focus:border-emerald-400"/></label>}

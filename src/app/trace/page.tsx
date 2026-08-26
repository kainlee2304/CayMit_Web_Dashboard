"use client";

import { FormEvent, useEffect, useState } from "react";
import { Boxes, CheckCircle2, Hash, MapPin, PackageCheck, QrCode, Search, ShieldCheck, XCircle } from "lucide-react";
import { getTraceBatch, TraceBatch } from "@/lib/api";
import TraceOperations from "@/components/TraceOperations";

const STAGE_LABELS: Record<string, string> = {
  created: "Khởi tạo", cultivation: "Canh tác", harvest: "Thu hoạch",
  processing: "Sơ chế", packing: "Đóng gói", cold_storage: "Kho lạnh",
  logistics: "Vận chuyển", export: "Xuất khẩu", market: "Thị trường",
};

const shortHash = (value: string) => `${value.slice(0, 10)}…${value.slice(-8)}`;

export default function TracePage() {
  const [code, setCode] = useState("");
  const [batch, setBatch] = useState<TraceBatch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const lookup = async (value: string) => {
    const normalized = value.trim().toUpperCase();
    if (!normalized) return;
    setLoading(true); setError(""); setBatch(null); setCode(normalized);
    try { setBatch(await getTraceBatch(normalized)); }
    catch { setError("Không tìm thấy lô nông sản. Vui lòng kiểm tra lại mã trên tem QR."); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get("code");
    if (initial) void lookup(initial);
  }, []);

  const submit = (event: FormEvent) => { event.preventDefault(); void lookup(code); };

  return <div className="mx-auto w-full max-w-5xl space-y-5 pb-10">
    <section className="overflow-hidden rounded-3xl border border-emerald-500/25 bg-gradient-to-br from-emerald-950 via-gray-900 to-gray-950 p-5 shadow-2xl sm:p-8">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="max-w-2xl"><div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-emerald-300"><ShieldCheck className="h-4 w-4"/> Blockchain truy xuất nguồn gốc</div><h1 className="text-2xl font-black text-white sm:text-4xl">Hành trình minh bạch của trái mít</h1><p className="mt-3 max-w-xl text-sm leading-6 text-gray-300 sm:text-base">Mỗi công đoạn được liên kết bằng mã băm SHA-256. Kiểm tra nơi trồng, đơn vị thực hiện và tính toàn vẹn của toàn bộ hành trình.</p></div>
        <div className="hidden h-28 w-28 flex-shrink-0 items-center justify-center rounded-3xl bg-white/10 sm:flex"><QrCode className="h-16 w-16 text-emerald-300"/></div>
      </div>
      <form onSubmit={submit} className="mt-6 flex flex-col gap-2 sm:flex-row"><label className="sr-only" htmlFor="trace-code">Mã truy xuất</label><input id="trace-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ví dụ: TM-260817-A1B2C3" className="min-h-12 min-w-0 flex-1 rounded-xl border border-gray-600 bg-gray-950/70 px-4 text-base font-semibold uppercase text-white outline-none placeholder:normal-case placeholder:text-gray-500 focus:border-emerald-400"/><button disabled={loading || !code.trim()} className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 font-bold text-white transition hover:bg-emerald-400 disabled:opacity-50"><Search className="h-5 w-5"/>{loading ? "Đang xác minh…" : "Xác minh"}</button></form>
    </section>

    <TraceOperations onBatch={(value)=>{setBatch(value);setCode(value.trace_code);setError("")}} />

    {error && <div className="flex items-start gap-3 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-red-200"><XCircle className="mt-0.5 h-5 w-5 flex-shrink-0"/><p>{error}</p></div>}

    {batch && <>
      <section className={`rounded-3xl border p-5 sm:p-6 ${batch.verified ? "border-emerald-500/30 bg-emerald-500/10" : "border-red-500/30 bg-red-500/10"}`}><div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-start gap-3">{batch.verified ? <CheckCircle2 className="h-8 w-8 flex-shrink-0 text-emerald-400"/> : <XCircle className="h-8 w-8 flex-shrink-0 text-red-400"/>}<div><p className={`text-lg font-black ${batch.verified ? "text-emerald-300" : "text-red-300"}`}>{batch.verified ? "Chuỗi dữ liệu toàn vẹn" : "Phát hiện dữ liệu không toàn vẹn"}</p><p className="mt-1 text-sm text-gray-300">Đã xác minh {batch.events.length} khối liên kết · Sổ cái nội bộ có cấp quyền</p></div></div><img src={batch.qr_url} alt={`QR truy xuất ${batch.trace_code}`} className="h-28 w-28 rounded-xl bg-white p-2"/></div></section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Info icon={PackageCheck} label="Sản phẩm" value={`${batch.product_name}${batch.variety ? ` · ${batch.variety}` : ""}`}/><Info icon={MapPin} label="Vùng trồng" value={batch.origin}/><Info icon={Boxes} label="Cơ sở" value={batch.farm_name}/><Info icon={Hash} label="Mã lô" value={batch.trace_code} mono/></section>

      <section className="rounded-3xl border border-gray-800 bg-gray-900 p-5 sm:p-7"><h2 className="text-xl font-black text-white">Dòng thời gian chuỗi giá trị</h2><div className="mt-6 space-y-0">{batch.events.map((item, index) => <article key={item.block_hash} className="relative grid grid-cols-[2.25rem_1fr] gap-3 pb-7 last:pb-0">{index < batch.events.length - 1 && <div className="absolute bottom-0 left-[1.05rem] top-8 w-px bg-emerald-500/30"/>}<div className="z-10 flex h-9 w-9 items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-500/15 text-xs font-black text-emerald-300">{item.block_index + 1}</div><div className="min-w-0 rounded-2xl border border-gray-800 bg-gray-950/60 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><span className="text-xs font-bold uppercase tracking-wider text-emerald-400">{STAGE_LABELS[item.stage] || item.stage}</span><h3 className="mt-1 font-bold text-white">{item.title}</h3></div><time className="text-xs text-gray-500">{new Date(item.event_time).toLocaleString("vi-VN")}</time></div><p className="mt-2 text-sm text-gray-300"><strong className="text-gray-200">Thực hiện:</strong> {item.actor}{item.location ? ` · ${item.location}` : ""}</p>{item.details && <p className="mt-2 text-sm leading-6 text-gray-400">{item.details}</p>}<p className="mt-3 overflow-hidden text-ellipsis whitespace-nowrap rounded-lg bg-gray-900 px-3 py-2 font-mono text-[11px] text-gray-500" title={item.block_hash}>SHA-256 {shortHash(item.block_hash)}</p></div></article>)}</div></section>
      <p className="text-center text-xs leading-5 text-gray-500">Blockchain trong hệ thống là chuỗi băm SHA-256 có cấp quyền, giúp phát hiện chỉnh sửa dữ liệu. Đây không phải xác nhận giao dịch trên mạng blockchain công khai.</p>
    </>}
  </div>;
}

function Info({ icon: Icon, label, value, mono = false }: { icon: typeof MapPin; label: string; value: string; mono?: boolean }) {
  return <div className="min-w-0 rounded-2xl border border-gray-800 bg-gray-900 p-4"><Icon className="h-5 w-5 text-emerald-400"/><p className="mt-3 text-xs uppercase tracking-wider text-gray-500">{label}</p><p className={`mt-1 break-words font-bold text-gray-100 ${mono ? "font-mono text-sm" : ""}`}>{value}</p></div>;
}

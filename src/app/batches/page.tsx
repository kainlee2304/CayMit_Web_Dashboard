"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { BrainCircuit, ChevronLeft, ChevronRight, CirclePlus, KeyRound, Lock, MapPin, Search, ShieldCheck } from "lucide-react";
import { AxiosError } from "axios";
import { appendTraceEvent, CLASS_LABELS, createTraceBatch, getTraceBatch, getTraceBatches, grantTraceBatchAccess, lockTraceBatch, MODEL_LABELS, Prediction, TraceBatch, uploadPredict } from "@/lib/api";
import { ROLE_LABELS, useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";
import { formatSafeDate } from "@/lib/utils";

const STAGE_LABELS_VI: Record<string, string> = {
  created: "Khởi tạo", cultivation: "Canh tác", harvest: "Thu hoạch",
  processing: "Sơ chế", packing: "Đóng gói", cold_storage: "Kho lạnh",
  logistics: "Vận chuyển", export: "Xuất khẩu", market: "Thị trường",
};

const STAGE_LABELS_EN: Record<string, string> = {
  created: "Initial Record", cultivation: "Cultivation", harvest: "Harvest",
  processing: "Processing", packing: "Packaging", cold_storage: "Cold Storage",
  logistics: "Logistics", export: "Export", market: "Retail Market",
};

const ROLE_STAGES: Record<string, string[]> = {
  admin_hq: ["cultivation", "harvest", "processing", "packing", "cold_storage", "logistics", "export", "market"],
  admin: ["cultivation", "harvest", "processing", "packing", "cold_storage", "logistics", "export", "market"],
  farmer: ["cultivation", "harvest"],
  producer: ["cultivation", "harvest"],
  technician: ["cultivation", "harvest"],
  packhouse_lead: ["processing", "packing", "cold_storage"],
  processor: ["processing", "packing", "cold_storage"],
  qa_qc: ["processing", "packing"],
  logistics: ["logistics", "export", "market"],
};

export default function BatchesPage() {
  const { user, token } = useAuth();
  const { locale, language } = useLanguage();
  const isEn = locale === "en" || language === "en";

  const stageLabels = isEn ? STAGE_LABELS_EN : STAGE_LABELS_VI;

  const [items, setItems] = useState<TraceBatch[]>([]);
  const [selected, setSelected] = useState<TraceBatch | null>(null);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [lot, setLot] = useState({
    product_name: "", variety: "", farm_name: "", origin: "", harvest_date: "", plot_code: "", quantity: "", unit: "kg"
  });
  const [event, setEvent] = useState({
    stage: user ? (ROLE_STAGES[user.role]?.[0] || "") : "", title: "", location: "", details: ""
  });
  const [accessUser, setAccessUser] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const data = await getTraceBatches(token, { page, page_size: 9, search: query, batch_status: status });
      setItems(data.items);
      setPages(Math.max(data.pages, 1));
      setTotal(data.total);
    } catch (e: unknown) {
      setError(detail(e));
    } finally {
      setLoading(false);
    }
  }, [token, page, query, status]);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (action: () => Promise<void>) => {
    setBusy(true); setError(""); setNotice("");
    try { await action(); }
    catch (e: unknown) { setError(detail(e)); }
    finally { setBusy(false); }
  };

  const canCreate = user?.role === "admin" || user?.role === "producer" || user?.role === "admin_hq" || user?.role === "farmer";
  const isOwner = !!user && (user.role === "admin" || user.role === "admin_hq" || selected?.owner_organization === user.organization);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 pb-10 font-sans">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-bold text-emerald-400">
            {isEn ? "SUPPLY CHAIN OPERATIONS" : "VẬN HÀNH CHUỖI CUNG ỨNG"}
          </p>
          <h1 className="mt-1 text-3xl font-black text-white">
            {isEn ? "Harvest Batch Management" : "Quản lý lô nông sản"}
          </h1>
          <p className="mt-1 text-sm text-gray-400">
            {isEn
              ? `Operating with role: ${user ? (ROLE_LABELS[user.role] || user.role) : ""}. Only authorized batches are accessible.`
              : `Bạn đang thao tác với quyền ${user ? ROLE_LABELS[user.role] : ""}; chỉ các lô thuộc phạm vi được cấp quyền mới xuất hiện.`}
          </p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900 px-4 py-3 text-sm">
          <strong className="text-white">{total}</strong>
          <span className="ml-1 text-gray-500">{isEn ? "batches accessible" : "lô được truy cập"}</span>
        </div>
      </header>

      {error && <Alert tone="red">{error}</Alert>}
      {notice && <Alert tone="green">{notice}</Alert>}

      {canCreate && (
        <details className="group rounded-2xl border border-gray-800 bg-gray-900" open={total === 0}>
          <summary className="flex cursor-pointer list-none items-center gap-2 p-5 font-bold text-white">
            <CirclePlus className="h-5 w-5 text-emerald-400" />
            {isEn ? "Create Harvest Batch Record" : "Tạo hồ sơ lô sản xuất"}
          </summary>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                const created = await createTraceBatch(token, { ...lot, quantity: lot.quantity ? Number(lot.quantity) : undefined });
                setSelected(created);
                setNotice(
                  isEn
                    ? `Created harvest batch ${created.trace_code}. Perform AI quality scan before transfer.`
                    : `Đã tạo lô ${created.trace_code}. Hãy kiểm định AI trước khi bàn giao.`
                );
                setLot({ product_name: "", variety: "", farm_name: "", origin: "", harvest_date: "", plot_code: "", quantity: "", unit: "kg" });
                setPage(1);
                await load();
              });
            }}
            className="grid gap-3 border-t border-gray-800 p-5 sm:grid-cols-2 lg:grid-cols-4"
          >
            <Field label={isEn ? "Product Name" : "Sản phẩm"} value={lot.product_name} set={(v) => setLot({ ...lot, product_name: v })} />
            <Field label={isEn ? "Variety" : "Giống"} value={lot.variety} set={(v) => setLot({ ...lot, variety: v })} optional />
            <Field label={isEn ? "Plot / PUC Code" : "Mã vùng trồng / thửa"} value={lot.plot_code} set={(v) => setLot({ ...lot, plot_code: v })} />
            <Field label={isEn ? "Farm of Origin" : "Cơ sở / vườn"} value={lot.farm_name} set={(v) => setLot({ ...lot, farm_name: v })} />
            <Field label={isEn ? "Origin / Location" : "Xuất xứ"} value={lot.origin} set={(v) => setLot({ ...lot, origin: v })} />
            <Field label={isEn ? "Quantity" : "Sản lượng"} type="number" value={lot.quantity} set={(v) => setLot({ ...lot, quantity: v })} />
            <Field label={isEn ? "Unit" : "Đơn vị"} value={lot.unit} set={(v) => setLot({ ...lot, unit: v })} />
            <Field label={isEn ? "Harvest Date" : "Ngày thu hoạch"} type="date" value={lot.harvest_date} set={(v) => setLot({ ...lot, harvest_date: v })} optional />
            <button
              disabled={busy}
              className="min-h-11 rounded-xl bg-emerald-500 px-5 font-bold text-white disabled:opacity-50 sm:col-span-2 lg:col-span-4"
            >
              {isEn ? "Create Batch & Issue QR Code" : "Tạo hồ sơ và mã QR"}
            </button>
          </form>
        </details>
      )}

      <section className="rounded-2xl border border-gray-800 bg-gray-900 p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setQuery(search);
          }}
          className="flex flex-col gap-2 sm:flex-row"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3.5 h-4 w-4 text-gray-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={isEn ? "Search by trace code, product, farm, or origin..." : "Mã lô, sản phẩm, cơ sở hoặc xuất xứ"}
              className="min-h-11 w-full rounded-xl border border-gray-700 bg-gray-950 pl-10 pr-3 text-sm text-white outline-none focus:border-emerald-400"
            />
          </div>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="min-h-11 rounded-xl border border-gray-700 bg-gray-950 px-3 text-sm text-white"
          >
            <option value="">{isEn ? "All Statuses" : "Tất cả trạng thái"}</option>
            {Object.entries(stageLabels).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <button className="min-h-11 rounded-xl bg-gray-700 px-5 text-sm font-bold text-white hover:bg-gray-600">
            {isEn ? "Search" : "Tìm kiếm"}
          </button>
        </form>
      </section>

      {loading ? (
        <Empty>{isEn ? "Loading batch directory..." : "Đang tải danh sách lô…"}</Empty>
      ) : items.length === 0 ? (
        <Empty>
          {isEn
            ? "No matching harvest batches found. Create a new batch or request access grant from the owner."
            : "Không có lô phù hợp. Hãy tạo lô mới hoặc nhờ chủ lô cấp quyền bằng tên đăng nhập."}
        </Empty>
      ) : (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((batch) => (
            <button
              key={batch.trace_code}
              onClick={() => setSelected(batch)}
              className={`rounded-2xl border p-5 text-left transition ${
                selected?.trace_code === batch.trace_code
                  ? "border-emerald-400 bg-emerald-500/10"
                  : "border-gray-800 bg-gray-900 hover:border-gray-600"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-mono text-xs font-bold text-emerald-400">{batch.trace_code}</span>
                <Status batch={batch} stageLabels={stageLabels} isEn={isEn} />
              </div>
              <h2 className="mt-3 text-lg font-black text-white">{batch.product_name}</h2>
              <p className="mt-1 text-sm text-gray-400">{batch.farm_name}</p>
              <p className="mt-3 flex items-center gap-1 text-xs text-gray-500">
                <MapPin className="h-3.5 w-3.5" />
                {batch.origin}
              </p>
              <div className="mt-4 flex items-center justify-between border-t border-gray-800 pt-3 text-xs text-gray-500">
                <span>{batch.events.length} {isEn ? "stages" : "công đoạn"}</span>
                <span>{batch.owner_organization || (isEn ? "Legacy Record" : "Dữ liệu cũ")}</span>
              </div>
            </button>
          ))}
        </section>
      )}

      <nav className="flex items-center justify-center gap-3">
        <button disabled={page <= 1} onClick={() => setPage((x) => x - 1)} className="rounded-xl border border-gray-700 p-2 disabled:opacity-30">
          <ChevronLeft />
        </button>
        <span className="text-sm text-gray-400">
          {isEn ? `Page ${page} of ${pages}` : `Trang ${page} / ${pages}`}
        </span>
        <button disabled={page >= pages} onClick={() => setPage((x) => x + 1)} className="rounded-xl border border-gray-700 p-2 disabled:opacity-30">
          <ChevronRight />
        </button>
      </nav>

      {selected && (
        <section className="rounded-3xl border border-gray-800 bg-gray-900 p-5 sm:p-7">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-2xl font-black text-white">{selected.product_name}</h2>
                <Status batch={selected} stageLabels={stageLabels} isEn={isEn} />
              </div>
              <p className="mt-1 font-mono text-sm text-emerald-400">{selected.trace_code}</p>
              <p className="mt-2 text-sm text-gray-400">
                {isEn ? "Owner:" : "Chủ lô:"} {selected.owner_organization || (isEn ? "Unassigned (Legacy)" : "Chưa xác định (dữ liệu cũ)")}
                {selected.plot_code ? ` · ${isEn ? "Plot" : "Vùng trồng"} ${selected.plot_code}` : ""}
                {selected.quantity ? ` · ${selected.quantity} ${selected.unit || ""}` : ""}
              </p>
            </div>
            <a
              href={`/trace?code=${selected.trace_code}`}
              className="rounded-xl border border-emerald-500/40 px-4 py-2 text-center text-sm font-bold text-emerald-300"
            >
              {isEn ? "View Public Passport" : "Xem trang công khai"}
            </a>
          </div>

          <BatchAiInspection token={token} batch={selected} onUpdated={setSelected} isEn={isEn} />

          <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_22rem]">
            <div>
              <h3 className="mb-3 font-bold text-white">
                {isEn ? "Cryptographic Ledger History" : "Lịch sử bất biến"}
              </h3>
              <div className="space-y-3">
                {selected.events.map((x) => {
                  const timeStr = formatSafeDate(x.event_time, language);
                  return (
                    <div key={x.block_hash} className="rounded-xl border border-gray-800 bg-gray-950/60 p-4">
                      <div className="flex flex-wrap justify-between gap-2">
                        <strong className="text-white">
                          {stageLabels[x.stage] || x.stage} · {x.title}
                        </strong>
                        <time className="text-xs text-gray-500">{timeStr}</time>
                      </div>
                      <p className="mt-1 text-sm text-gray-400">
                        {x.actor}{x.location ? ` · ${x.location}` : ""}
                      </p>
                      {x.details && <p className="mt-2 text-sm text-gray-500">{x.details}</p>}
                    </div>
                  );
                })}
              </div>
            </div>

            <aside className="space-y-4">
              {!selected.locked && (
                <form
                  onSubmit={(e: FormEvent) => {
                    e.preventDefault();
                    void run(async () => {
                      const updated = await appendTraceEvent(token, selected.trace_code, event);
                      setSelected(updated);
                      setNotice(isEn ? "Recorded new stage block" : "Đã ghi công đoạn mới");
                      setEvent({ ...event, title: "", location: "", details: "" });
                      await load();
                    });
                  }}
                  className="space-y-3 rounded-2xl border border-gray-800 bg-gray-950/60 p-4"
                >
                  <h3 className="font-bold text-white">
                    {isEn ? "Append Supply Chain Stage" : "Ghi công đoạn"}
                  </h3>
                  <select
                    value={event.stage}
                    onChange={(e) => setEvent({ ...event, stage: e.target.value })}
                    className="min-h-11 w-full rounded-xl border border-gray-700 bg-gray-900 px-3 text-sm text-white"
                  >
                    {user &&
                      (ROLE_STAGES[user.role] || []).map((x: string) => (
                        <option key={x} value={x}>
                          {stageLabels[x] || x}
                        </option>
                      ))}
                  </select>
                  <Field label={isEn ? "Event Title" : "Nội dung"} value={event.title} set={(v) => setEvent({ ...event, title: v })} />
                  <Field label={isEn ? "Location" : "Địa điểm"} value={event.location} set={(v) => setEvent({ ...event, location: v })} optional />
                  <Field label={isEn ? "Notes / Certificate Ref" : "Ghi chú / chứng từ"} value={event.details} set={(v) => setEvent({ ...event, details: v })} optional />
                  <button
                    disabled={busy || !event.title}
                    className="min-h-11 w-full rounded-xl bg-emerald-500 font-bold text-white disabled:opacity-40"
                  >
                    {isEn ? "Confirm & Commit Block" : "Xác nhận công đoạn"}
                  </button>
                </form>
              )}

              {isOwner && !selected.locked && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void run(async () => {
                      await grantTraceBatchAccess(token, selected.trace_code, accessUser);
                      setNotice(isEn ? `Granted access to ${accessUser}` : `Đã cấp quyền cho ${accessUser}`);
                      setAccessUser("");
                    });
                  }}
                  className="space-y-3 rounded-2xl border border-gray-800 bg-gray-950/60 p-4"
                >
                  <h3 className="flex items-center gap-2 font-bold text-white">
                    <KeyRound className="h-4 w-4 text-blue-400" />
                    {isEn ? "Grant Partner Access" : "Cấp quyền đối tác"}
                  </h3>
                  <Field label={isEn ? "Partner Username" : "Tên đăng nhập đối tác"} value={accessUser} set={setAccessUser} />
                  <button disabled={busy} className="min-h-10 w-full rounded-xl bg-blue-500 font-bold text-white">
                    {isEn ? "Grant Batch Access" : "Cấp quyền vào lô"}
                  </button>
                </form>
              )}

              {isOwner && !selected.locked && (
                <button
                  onClick={() => {
                    if (confirm(isEn ? "Sealing batch will permanently lock new entries. Continue?" : "Khóa lô sẽ không thể ghi thêm công đoạn. Tiếp tục?")) {
                      void run(async () => {
                        const updated = await lockTraceBatch(token, selected.trace_code);
                        setSelected(updated);
                        setNotice(isEn ? "Batch ledger sealed and locked." : "Đã khóa hồ sơ lô");
                      });
                    }
                  }}
                  className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-amber-500/40 text-sm font-bold text-amber-300"
                >
                  <Lock className="h-4 w-4" />
                  {isEn ? "Seal & Lock Batch" : "Khóa hồ sơ lô"}
                </button>
              )}

              {selected.locked && (
                <Alert tone="green">
                  <ShieldCheck className="mr-2 inline h-4 w-4" />
                  {isEn ? "Batch record sealed & immutable. No further modifications allowed." : "Hồ sơ đã khóa, không thể ghi thêm dữ liệu."}
                </Alert>
              )}
            </aside>
          </div>
        </section>
      )}
    </div>
  );
}

function detail(e: unknown) {
  return (e as AxiosError<{ detail?: string }>)?.response?.data?.detail || "Không thể thực hiện thao tác. Vui lòng thử lại.";
}

function Status({ batch, stageLabels, isEn }: { batch: TraceBatch; stageLabels: Record<string, string>; isEn: boolean }) {
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${batch.locked ? "bg-blue-500/15 text-blue-300" : "bg-emerald-500/15 text-emerald-300"}`}>
      {batch.locked ? (isEn ? "Sealed" : "Đã khóa") : stageLabels[batch.status] || batch.status}
    </span>
  );
}

function Field({ label, value, set, type = "text", optional = false }: { label: string; value: string; set: (v: string) => void; type?: string; optional?: boolean }) {
  return (
    <label className="block text-xs font-bold text-gray-400">
      {label}
      <input
        required={!optional}
        type={type}
        value={value}
        onChange={(e) => set(e.target.value)}
        className="mt-1.5 min-h-11 w-full rounded-xl border border-gray-700 bg-gray-900 px-3 text-sm text-white outline-none focus:border-emerald-400"
      />
    </label>
  );
}

function Alert({ children, tone }: { children: React.ReactNode; tone: "red" | "green" }) {
  return (
    <div className={`rounded-xl border p-3 text-sm ${tone === "red" ? "border-red-500/30 bg-red-500/10 text-red-300" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"}`}>
      {children}
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-gray-700 py-16 text-center text-sm text-gray-500">{children}</div>;
}

function BatchAiInspection({ token, batch, onUpdated, isEn }: { token: string; batch: TraceBatch; onUpdated: (batch: TraceBatch) => void; isEn: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState("best_11");
  const [result, setResult] = useState<Prediction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (batch.locked) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true); setError("");
    try {
      const value = await uploadPredict(file, model, batch.trace_code);
      setResult(value);
      onUpdated(await getTraceBatch(batch.trace_code));
      setFile(null);
    } catch (e: unknown) {
      setError(detail(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mt-6 rounded-2xl border border-blue-500/25 bg-blue-500/5 p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <BrainCircuit className="h-6 w-6 text-blue-400" />
        <div>
          <h3 className="font-black text-white">
            {isEn ? "AI Quality & Health Diagnostic Inspection" : "Kiểm định chất lượng bằng AI"}
          </h3>
          <p className="mt-1 text-sm text-gray-400">
            {isEn
              ? `Inspection photo and diagnostic output will be appended to batch ${batch.trace_code} as a block in the hash ledger.`
              : `Ảnh và kết quả nhận diện sẽ gắn với lô ${batch.trace_code} và trở thành một block trong hành trình truy xuất.`}
          </p>
        </div>
      </div>
      <form onSubmit={submit} className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <input
          required
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="min-h-11 rounded-xl border border-gray-700 bg-gray-950 p-2 text-sm text-gray-300"
        />
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="min-h-11 rounded-xl border border-gray-700 bg-gray-950 px-3 text-sm text-white"
        >
          {Object.entries(MODEL_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
        <button
          disabled={busy || !file}
          className="min-h-11 rounded-xl bg-blue-500 px-5 font-bold text-white disabled:opacity-40"
        >
          {busy ? (isEn ? "Analyzing..." : "Đang phân tích…") : (isEn ? "Analyze & Append Block" : "Phân tích & ghi vào lô")}
        </button>
      </form>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
      {result && (
        <p className="mt-3 rounded-xl bg-gray-950 p-3 text-sm text-gray-300">
          {isEn ? "Result:" : "Kết quả:"}{" "}
          <strong className="text-blue-300">{CLASS_LABELS[result.predicted_class] || result.predicted_class}</strong> · {(result.confidence * 100).toFixed(1)}% · {MODEL_LABELS[result.model_used] || result.model_used}
        </p>
      )}
    </section>
  );
}

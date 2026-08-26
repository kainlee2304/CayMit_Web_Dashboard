"use client";
import { useState } from "react";
import useSWR from "swr";
import { X, AlertTriangle, ShieldCheck, Leaf, CheckCircle, ChevronRight } from "lucide-react";
import {
    getPredictions, CLASS_LABELS, CLASS_COLORS, DISEASE_TREATMENTS, Prediction, isHealthyClass,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ||
    (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
const CLASSES = ["", "pink_disease", "stem_cracking_gummosis", "batocera_rufomaculata", "stripe_canker", "Sau_duc_trai(BactroceraSpp)", "ThoiTrai(Rhizopus_stolonifer)", "Binh_thuong", "Healthy"];

// ── Group predictions by date ────────────────────────────────────────
function groupByDay(predictions: Prediction[]): Record<string, Prediction[]> {
    return predictions.reduce((acc, p) => {
        const day = new Date(p.created_at).toLocaleDateString("vi-VN", {
            weekday: "long", year: "numeric", month: "long", day: "numeric",
        });
        if (!acc[day]) acc[day] = [];
        acc[day].push(p);
        return acc;
    }, {} as Record<string, Prediction[]>);
}

// ── Severity badge ───────────────────────────────────────────────────
function SeverityBadge({ severity }: { severity: string }) {
    const map = {
        high: { label: "Nguy hiểm", cls: "bg-red-500/20 text-red-400 border-red-500/30" },
        medium: { label: "Trung bình", cls: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
        low: { label: "Bình thường", cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
    };
    const s = map[severity as keyof typeof map] || map.low;
    return (
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${s.cls}`}>{s.label}</span>
    );
}

// ── Detail Modal ─────────────────────────────────────────────────────
function DetailModal({ p, onClose }: { p: Prediction; onClose: () => void }) {
    const color = CLASS_COLORS[p.predicted_class] || "#94a3b8";
    const label = CLASS_LABELS[p.predicted_class] || p.predicted_class;
    const treatment = DISEASE_TREATMENTS[p.predicted_class];
    const imgName = p.image_path?.split(/[/\\]/).pop();
    const isHealthy = isHealthyClass(p.predicted_class);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-2 backdrop-blur-sm sm:p-4"
            onClick={onClose}>
            <div
                className="bg-gray-950 border border-gray-800 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-gray-800 bg-gray-950 px-4 py-4 sm:items-center sm:px-6">
                    <div className="flex min-w-0 flex-wrap items-center gap-2 sm:gap-3">
                        <span className="w-3 h-3 rounded-full" style={{ background: color }} />
                        <h2 className="min-w-0 break-words text-base font-bold text-white sm:text-lg">{label}</h2>
                        {treatment && <SeverityBadge severity={treatment.severity} />}
                    </div>
                    <button onClick={onClose} className="text-gray-500 hover:text-white transition p-1">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="space-y-5 p-4 sm:space-y-6 sm:p-6">
                    {/* Image + basic info */}
                    <div className="grid sm:grid-cols-2 gap-5">
                        {imgName ? (
                            <img
                                src={`${API_URL}/uploads/${imgName}`}
                                alt={label}
                                className="w-full rounded-xl object-cover border border-gray-800"
                                style={{ maxHeight: 280 }}
                            />
                        ) : (
                            <div className="w-full rounded-xl bg-gray-900 border border-gray-800 flex items-center justify-center" style={{ height: 200 }}>
                                <Leaf className="w-12 h-12 text-gray-700" />
                            </div>
                        )}

                        <div className="space-y-3">
                            <div className="bg-gray-900 rounded-xl p-4">
                                <p className="text-gray-500 text-xs mb-1">Confidence</p>
                                <p className="text-3xl font-bold" style={{ color }}>{(p.confidence * 100).toFixed(1)}%</p>
                            </div>
                            {/* Scores bar */}
                            <div className="bg-gray-900 rounded-xl p-4 space-y-2">
                                <p className="text-gray-500 text-xs mb-2">Điểm phân tích</p>
                                {Object.entries(p.all_scores || {}).map(([c, v]) => (
                                    <div key={c} className="grid grid-cols-[minmax(72px,120px)_minmax(0,1fr)_36px] items-center gap-2">
                                        <div className="flex items-center gap-1.5 min-w-0">
                                            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CLASS_COLORS[c] || "#94a3b8" }} />
                                            <span className="text-gray-400 text-xs truncate">{CLASS_LABELS[c] || c}</span>
                                        </div>
                                        <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                                            <div className="h-full rounded-full" style={{ width: `${v * 100}%`, background: CLASS_COLORS[c] || "#94a3b8" }} />
                                        </div>
                                        <span className="text-gray-500 text-xs w-9 text-right">{(v * 100).toFixed(0)}%</span>
                                    </div>
                                ))}
                            </div>
                            <p className="text-gray-600 text-xs px-1">
                                📅 {new Date(p.created_at).toLocaleString("vi-VN")}<br />
                                🤖 Model: {p.model_used}
                            </p>
                        </div>
                    </div>

                    {treatment && !isHealthy && (
                        <>
                            {/* Cause & symptoms */}
                            <div className="grid sm:grid-cols-2 gap-4">
                                <div className="bg-red-950/30 border border-red-900/40 rounded-xl p-4">
                                    <div className="flex items-center gap-2 mb-2">
                                        <AlertTriangle className="w-4 h-4 text-red-400" />
                                        <span className="text-red-400 font-semibold text-sm">Nguyên nhân</span>
                                    </div>
                                    <p className="text-gray-300 text-sm leading-relaxed">{treatment.cause}</p>
                                </div>
                                <div className="bg-orange-950/30 border border-orange-900/40 rounded-xl p-4">
                                    <div className="flex items-center gap-2 mb-2">
                                        <AlertTriangle className="w-4 h-4 text-orange-400" />
                                        <span className="text-orange-400 font-semibold text-sm">Triệu chứng</span>
                                    </div>
                                    <p className="text-gray-300 text-sm leading-relaxed">{treatment.symptoms}</p>
                                </div>
                            </div>

                            {/* Treatment steps */}
                            <div className="bg-blue-950/30 border border-blue-900/40 rounded-xl p-5">
                                <div className="flex items-center gap-2 mb-4">
                                    <ShieldCheck className="w-5 h-5 text-blue-400" />
                                    <h3 className="text-blue-400 font-semibold">Biện pháp xử lý</h3>
                                </div>
                                <ol className="space-y-3">
                                    {treatment.steps.map((step, i) => (
                                        <li key={i} className="flex gap-3 items-start">
                                            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500/20 border border-blue-500/40 text-blue-400 text-xs font-bold flex items-center justify-center mt-0.5">
                                                {i + 1}
                                            </span>
                                            <p className="text-gray-300 text-sm leading-relaxed">{step}</p>
                                        </li>
                                    ))}
                                </ol>
                            </div>

                            {/* Prevention */}
                            <div className="bg-emerald-950/30 border border-emerald-900/40 rounded-xl p-5">
                                <div className="flex items-center gap-2 mb-4">
                                    <CheckCircle className="w-5 h-5 text-emerald-400" />
                                    <h3 className="text-emerald-400 font-semibold">Phòng ngừa</h3>
                                </div>
                                <ul className="space-y-2">
                                    {treatment.prevention.map((tip, i) => (
                                        <li key={i} className="flex gap-2 items-start">
                                            <ChevronRight className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                                            <p className="text-gray-300 text-sm">{tip}</p>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </>
                    )}

                    {treatment && isHealthy && (
                        <div className="bg-emerald-950/30 border border-emerald-900/40 rounded-xl p-5 text-center">
                            <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
                            <p className="text-emerald-400 font-semibold">Cây đang khỏe mạnh!</p>
                            <p className="text-gray-400 text-sm mt-1">Duy trì chế độ chăm sóc hiện tại và tiếp tục theo dõi định kỳ.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// ── Main History Page ────────────────────────────────────────────────
export default function HistoryPage() {
    const [filterClass, setFilterClass] = useState("");
    const [page, setPage] = useState(0);
    const [selected, setSelected] = useState<Prediction | null>(null);
    const limit = 40;

    const { data: predictions = [], isLoading } = useSWR<Prediction[]>(
        ["predictions", filterClass, page],
        () => getPredictions({ limit, skip: page * limit, ...(filterClass ? { predicted_class: filterClass } : {}) }),
        { refreshInterval: 15000 }
    );

    const grouped = groupByDay(predictions);
    const days = Object.keys(grouped);

    return (
        <div className="mx-auto w-full max-w-7xl space-y-5 sm:space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-white">Lịch Sử Phát Hiện</h1>
                <p className="text-gray-500 text-sm mt-0.5">Kết quả phân tích theo ngày — click ảnh để xem chi tiết & khắc phục</p>
            </div>

            {/* Filter */}
            <div className="-mx-3 flex gap-2 overflow-x-auto px-3 pb-2 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
                {CLASSES.map((cls) => (
                    <button
                        key={cls}
                        onClick={() => { setFilterClass(cls); setPage(0); }}
                        className={`flex-shrink-0 px-4 py-2 rounded-xl text-sm font-medium transition-all ${filterClass === cls
                                ? "text-white shadow-lg"
                                : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white"
                            }`}
                        style={filterClass === cls ? { background: CLASS_COLORS[cls] || "#10b981" } : undefined}
                    >
                        {cls ? CLASS_LABELS[cls] || cls : "Tất Cả"}
                    </button>
                ))}
            </div>

            {/* Content */}
            {isLoading ? (
                <div className="text-center py-20 text-gray-500">Đang tải...</div>
            ) : predictions.length === 0 ? (
                <div className="text-center py-20 text-gray-500">Chưa có dữ liệu</div>
            ) : (
                <div className="space-y-8">
                    {days.map((day) => (
                        <div key={day}>
                            {/* Day header */}
                            <div className="mb-4 flex min-w-0 items-center gap-2 sm:gap-3">
                                <div className="h-px flex-1 bg-gray-800" />
                                <span className="max-w-[70vw] truncate rounded-full border border-gray-800 bg-gray-900 px-3 py-1 text-xs font-medium text-gray-400 sm:max-w-none sm:text-sm">
                                    📅 {day}
                                </span>
                                <span className="text-gray-600 text-xs">{grouped[day].length} ảnh</span>
                                <div className="h-px flex-1 bg-gray-800" />
                            </div>

                            {/* Grid */}
                            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {grouped[day].map((p) => {
                                    const color = CLASS_COLORS[p.predicted_class] || "#94a3b8";
                                    const label = CLASS_LABELS[p.predicted_class] || p.predicted_class;
                                    const imgName = p.image_path?.split(/[/\\]/).pop();
                                    return (
                                        <button
                                            key={p.id}
                                            onClick={() => setSelected(p)}
                                            className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden hover:border-gray-500 hover:scale-[1.02] transition-all text-left group"
                                        >
                                            <div className="relative">
                                                {imgName ? (
                                                    <img
                                                        src={`${API_URL}/uploads/${imgName}`}
                                                        alt={label}
                                                        className="w-full h-44 object-cover"
                                                    />
                                                ) : (
                                                    <div className="w-full h-44 bg-gray-800 flex items-center justify-center">
                                                        <Leaf className="w-8 h-8 text-gray-600" />
                                                    </div>
                                                )}
                                                {/* Hover overlay */}
                                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                                                    <span className="opacity-0 group-hover:opacity-100 text-white text-xs font-medium bg-black/60 px-3 py-1.5 rounded-full transition-all">
                                                        Xem chi tiết →
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="p-4">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                                                    <span className="font-semibold text-white text-sm truncate">{label}</span>
                                                </div>
                                                <div className="flex items-center justify-between mt-2">
                                                    <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                                                        style={{ background: color + "22", color }}>
                                                        {(p.confidence * 100).toFixed(1)}%
                                                    </span>
                                                    <span className="text-gray-600 text-xs">
                                                        {new Date(p.created_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}
                                                    </span>
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Pagination */}
            <div className="flex gap-2 justify-center pt-2">
                <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}
                    className="px-4 py-2 bg-gray-800 rounded-xl text-sm disabled:opacity-40 hover:bg-gray-700 transition">
                    Trước
                </button>
                <span className="px-4 py-2 text-gray-400 text-sm">Trang {page + 1}</span>
                <button disabled={predictions.length < limit} onClick={() => setPage((p) => p + 1)}
                    className="px-4 py-2 bg-gray-800 rounded-xl text-sm disabled:opacity-40 hover:bg-gray-700 transition">
                    Tiếp
                </button>
            </div>

            {/* Detail Modal */}
            {selected && <DetailModal p={selected} onClose={() => setSelected(null)} />}
        </div>
    );
}

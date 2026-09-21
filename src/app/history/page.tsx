"use client";
import { useState } from "react";
import useSWR from "swr";
import { X, Leaf, CheckCircle } from "lucide-react";
import { useLanguage } from "@/context/LanguageContext";
import {
    getPredictionsPage, CLASS_LABELS, getClassLabel, CLASS_COLORS, DISEASE_TREATMENTS, Prediction, PredictionPage, isHealthyClass,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ||
    (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
const CLASSES = ["", "pink_disease", "stem_cracking_gummosis", "batocera_rufomaculata", "stripe_canker", "Sau_duc_trai(BactroceraSpp)", "ThoiTrai(Rhizopus_stolonifer)", "Binh_thuong", "Healthy"];

function formatSafeTime(dateVal: any, lang: string): string {
    if (!dateVal) return "—";
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleTimeString(lang === "en" ? "en-US" : "vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function groupByDay(predictions: Prediction[], lang: string): Record<string, Prediction[]> {
    return predictions.reduce((acc, p) => {
        const d = new Date(p.created_at);
        const day = isNaN(d.getTime())
            ? (lang === "en" ? "Unknown Date" : "Ngày không xác định")
            : d.toLocaleDateString(lang === "en" ? "en-US" : "vi-VN", {
                weekday: "long", year: "numeric", month: "long", day: "numeric",
            });
        if (!acc[day]) acc[day] = [];
        acc[day].push(p);
        return acc;
    }, {} as Record<string, Prediction[]>);
}

// ── Severity badge ───────────────────────────────────────────────────
function SeverityBadge({ severity, lang }: { severity: string; lang: string }) {
    const mapEn = {
        high: { label: "High Risk", cls: "bg-red-500/20 text-red-400 border-red-500/30" },
        medium: { label: "Moderate", cls: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
        low: { label: "Normal", cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
    };
    const mapVi = {
        high: { label: "Nguy hiểm", cls: "bg-red-500/20 text-red-400 border-red-500/30" },
        medium: { label: "Trung bình", cls: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
        low: { label: "Bình thường", cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
    };
    const map = lang === "en" ? mapEn : mapVi;
    const s = map[severity as keyof typeof map] || map.low;
    return (
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${s.cls}`}>{s.label}</span>
    );
}

// ── Detail Modal ─────────────────────────────────────────────────────
function DetailModal({ p, onClose, lang, t }: { p: Prediction; onClose: () => void; lang: string; t: any }) {
    const color = CLASS_COLORS[p.predicted_class] || "#94a3b8";
    const label = CLASS_LABELS[p.predicted_class] || p.predicted_class;
    const treatment = DISEASE_TREATMENTS[p.predicted_class];
    const imgName = p.image_path?.split(/[/\\]/).pop();

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-2 backdrop-blur-sm sm:p-4 font-sans"
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
                        {treatment && <SeverityBadge severity={treatment.severity} lang={lang} />}
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
                                <p className="text-gray-500 text-xs mb-1">{t.live.confidence}</p>
                                <p className="text-3xl font-bold" style={{ color }}>{(p.confidence * 100).toFixed(1)}%</p>
                            </div>
                            {/* Scores bar */}
                            <div className="bg-gray-900 rounded-xl p-4 space-y-2">
                                <p className="text-gray-500 text-xs mb-2">{t.live.resultTitle}</p>
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
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function HistoryPage() {
    const { t, language } = useLanguage();
    const [filterClass, setFilterClass] = useState("");
    const [page, setPage] = useState(1);
    const [selected, setSelected] = useState<Prediction | null>(null);

    const params: Record<string, string | number> = { page, page_size: 16 };
    if (filterClass) params.predicted_class = filterClass;

    const { data, isLoading } = useSWR<PredictionPage>(
        ["predictions", params],
        () => getPredictionsPage(params)
    );

    const predictions = data?.items || [];
    const grouped = groupByDay(predictions, language);
    const days = Object.keys(grouped);

    return (
        <div className="mx-auto w-full max-w-7xl space-y-6 font-sans">
            <div>
                <h1 className="text-2xl font-bold text-white">{t.history.title}</h1>
                <p className="text-gray-500 text-sm mt-0.5">{t.history.subtitle}</p>
            </div>

            {/* Filter */}
            <div className="-mx-3 flex gap-2 overflow-x-auto px-3 pb-2 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
                {CLASSES.map((cls) => (
                    <button
                        key={cls}
                        onClick={() => { setFilterClass(cls); setPage(1); }}
                        className={`flex-shrink-0 px-4 py-2 rounded-xl text-sm font-medium transition-all ${filterClass === cls
                            ? "text-white shadow-lg"
                            : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white"
                        }`}
                        style={filterClass === cls ? { background: CLASS_COLORS[cls] || "#10b981" } : undefined}
                    >
                        {cls ? getClassLabel(cls, language) : (language === "en" ? "All" : "Tất Cả")}
                    </button>
                ))}
            </div>

            {/* Content */}
            {isLoading ? (
                <div className="text-center py-20 text-gray-500">{t.common.loading}</div>
            ) : predictions.length === 0 ? (
                <div className="text-center py-20 text-gray-500">{t.common.noData}</div>
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
                                <span className="text-gray-600 text-xs">{grouped[day].length} {language === "en" ? "scans" : "ảnh"}</span>
                                <div className="h-px flex-1 bg-gray-800" />
                            </div>

                            {/* Grid */}
                            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {grouped[day].map((p) => {
                                    const color = CLASS_COLORS[p.predicted_class] || "#94a3b8";
                                    const label = getClassLabel(p.predicted_class, language);
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
                                                        {t.common.viewDetails} →
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="p-4">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                                                    <span className="font-semibold text-white text-sm truncate">{label}</span>
                                                </div>
                                                {p.trace_code && (
                                                    <a href={`/trace/?code=${p.trace_code}`} onClick={(e) => e.stopPropagation()} className="mt-2 block font-mono text-xs text-emerald-400 hover:underline">
                                                        {language === "en" ? "Batch" : "Lô"} {p.trace_code}
                                                    </a>
                                                )}
                                                <div className="flex items-center justify-between mt-2">
                                                    <span className="text-xs px-2 py-0.5 rounded-full font-medium"
                                                        style={{ background: color + "22", color }}>
                                                        {(p.confidence * 100).toFixed(1)}%
                                                    </span>
                                                    <span className="text-gray-600 text-xs">
                                                        {formatSafeTime(p.created_at, language)}
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
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}
                    className="px-4 py-2 bg-gray-800 rounded-xl text-sm disabled:opacity-40 hover:bg-gray-700 transition">
                    {language === "en" ? "Previous" : "Trước"}
                </button>
                <span className="px-4 py-2 text-gray-400 text-sm">
                    {language === "en" ? "Page" : "Trang"} {page} / {Math.max(data?.pages || 0, 1)} · {data?.total || 0} {t.common.allResultsCount}
                </span>
                <button disabled={page >= (data?.pages || 1)} onClick={() => setPage((p) => p + 1)}
                    className="px-4 py-2 bg-gray-800 rounded-xl text-sm disabled:opacity-40 hover:bg-gray-700 transition">
                    {language === "en" ? "Next" : "Tiếp"}
                </button>
            </div>

            {/* Detail Modal */}
            {selected && <DetailModal p={selected} onClose={() => setSelected(null)} lang={language} t={t} />}
        </div>
    );
}

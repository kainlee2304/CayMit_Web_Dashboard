"use client";
import { useState } from "react";
import useSWR from "swr";
import { Eye, EyeOff, Camera, Timer, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";
import { useCapture } from "@/context/CaptureContext";
import { CLASS_LABELS, CLASS_COLORS, FALLBACK_MODELS, MODEL_LABELS, ModelInfo, getModels, getOverallAdvice } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ||
    (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

export default function LivePage() {
    const {
        selectedModel, setSelectedModel,
        autoCapture, setAutoCapture,
        intervalMin, setIntervalMin,
        capturing, countdown, lastResult, doCapture,
    } = useCapture();

    const { data: loadedModels } = useSWR<ModelInfo[]>("models", getModels);
    const [aiMode, setAiMode] = useState(false);
    const [streamKey, setStreamKey] = useState(0);
    const modelOptions = loadedModels?.length ? loadedModels : FALLBACK_MODELS;
    const advice = getOverallAdvice(lastResult);

    const streamUrl = aiMode
        ? `${API_URL}/api/stream/camera/ai?model_name=${encodeURIComponent(selectedModel)}`
        : `${API_URL}/api/stream/camera`;

    const cls = lastResult?.predicted_class;
    const color = cls ? CLASS_COLORS[cls] || "#94a3b8" : "#94a3b8";
    const label = cls ? CLASS_LABELS[cls] || cls : "";
    const isHealthy = cls === "Binh_thuong";
    const mm = String(Math.floor(countdown / 60)).padStart(2, "0");
    const ss = String(countdown % 60).padStart(2, "0");

    return (
        <div className="mx-auto w-full max-w-5xl space-y-5">
            <div>
                <h1 className="text-2xl font-bold text-white">Camera Live</h1>
                <p className="text-gray-500 text-sm mt-0.5">Xem camera + tự động phân tích bệnh định kỳ</p>
            </div>

            {/* ── Controls ──────────────────────────────────────────── */}
            <div className="grid grid-cols-1 gap-3 sm:flex sm:flex-wrap sm:items-center">
                <button
                    onClick={() => setStreamKey((k) => k + 1)}
                    className="flex min-h-11 items-center justify-center gap-2 rounded-xl bg-gray-800 px-4 py-2 text-sm text-gray-300 transition hover:bg-gray-700"
                >
                    <RefreshCw className="w-4 h-4" /> Kết nối lại
                </button>

                <button
                    onClick={() => { setAiMode((v) => !v); setStreamKey((k) => k + 1); }}
                    className={`flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${aiMode ? "bg-violet-500/20 border border-violet-500/40 text-violet-400" : "bg-gray-800 border border-gray-700 text-gray-400"
                        }`}
                >
                    {aiMode ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    Overlay AI: {aiMode ? "BẬT" : "TẮT"}
                </button>

                <button
                    onClick={doCapture}
                    disabled={capturing}
                    className="flex min-h-11 items-center justify-center gap-2 rounded-xl border border-blue-500/40 bg-blue-500/20 px-4 py-2 text-sm font-medium text-blue-400 transition hover:bg-blue-500/30 disabled:opacity-50"
                >
                    <Camera className="w-4 h-4" />
                    {capturing ? "Đang chụp..." : "Chụp Ngay"}
                </button>

                <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="min-h-11 w-full rounded-xl border border-gray-800 bg-gray-900 px-3 py-2 text-sm text-white outline-none focus:border-emerald-500 sm:w-auto sm:max-w-xs"
                >
                    {modelOptions.map((model) => (
                        <option key={model.name} value={model.name}>
                            {MODEL_LABELS[model.name] || model.name}
                        </option>
                    ))}
                </select>

                {/* Interval input */}
                <div className="flex min-h-11 items-center justify-center gap-2 rounded-xl border border-gray-800 bg-gray-900 px-3 py-1.5 sm:justify-start">
                    <Timer className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <input
                        type="number" min={1} max={60}
                        value={intervalMin}
                        onChange={(e) => setIntervalMin(Math.max(1, parseInt(e.target.value) || 1))}
                        className="w-12 bg-transparent text-white text-sm text-center outline-none"
                    />
                    <span className="text-gray-400 text-sm">phút</span>
                </div>

                {/* Auto toggle */}
                <button
                    onClick={() => setAutoCapture(!autoCapture)}
                    className={`flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-2 text-sm font-medium transition-all ${autoCapture
                            ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/30"
                            : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                        }`}
                >
                    <div className={`w-2 h-2 rounded-full ${autoCapture ? "bg-white animate-pulse" : "bg-gray-600"}`} />
                    Tự động: {autoCapture ? "BẬT" : "TẮT"}
                </button>
            </div>

            {/* ── Countdown bar ─────────────────────────────────────── */}
            {autoCapture && (
                <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-800 bg-gray-900 px-4 py-3 sm:gap-4 sm:px-5">
                    <span className="text-gray-400 text-sm">Chụp tiếp theo sau:</span>
                    <span className="text-emerald-400 font-mono font-bold text-lg">{mm}:{ss}</span>
                    <div className="order-last h-1.5 w-full overflow-hidden rounded-full bg-gray-800 sm:order-none sm:w-auto sm:flex-1">
                        <div
                            className="h-full bg-emerald-500 transition-all duration-1000"
                            style={{ width: `${(1 - countdown / (intervalMin * 60)) * 100}%` }}
                        />
                    </div>
                    <span className="text-xs text-gray-600">🔁 Chạy xuyên trang</span>
                </div>
            )}

            <div className="grid min-w-0 gap-5 lg:grid-cols-3">
                {/* ── Stream ─────────────────────────────────────────── */}
                <div className="min-w-0 overflow-hidden rounded-2xl border border-gray-800 bg-gray-900 lg:col-span-2">
                    <div className="relative bg-black" style={{ aspectRatio: "16/9" }}>
                        <img key={streamKey} src={streamUrl} alt="camera" className="w-full h-full object-contain" />
                        <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur px-3 py-1.5 rounded-full">
                            <div className={`w-2 h-2 rounded-full animate-pulse ${aiMode ? "bg-violet-400" : "bg-emerald-400"}`} />
                            <span className={`text-xs font-medium ${aiMode ? "text-violet-300" : "text-emerald-300"}`}>
                                {aiMode ? "AI Detection" : "Live"}
                            </span>
                        </div>
                        {capturing && (
                            <div className="absolute inset-0 border-4 border-white/40 animate-pulse pointer-events-none" />
                        )}
                    </div>
                </div>

                {/* ── Result ─────────────────────────────────────────── */}
                <div className="flex min-w-0 flex-col rounded-2xl border border-gray-800 bg-gray-900 p-4 sm:p-5">
                    <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                        <Camera className="w-4 h-4 text-gray-400" /> Kết Quả
                    </h2>

                    {!lastResult ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
                            <Camera className="w-10 h-10 opacity-30" />
                            Chưa chụp ảnh nào
                        </div>
                    ) : (
                        <div className="space-y-4 flex-1">
                            {lastResult.image_filename && (
                                <img
                                    src={`${API_URL}/uploads/${lastResult.image_filename}`}
                                    alt="captured"
                                    className="w-full rounded-xl object-cover border border-gray-700"
                                    style={{ maxHeight: 150 }}
                                />
                            )}
                            <div
                                className="rounded-xl p-4 text-center"
                                style={{ background: color + "18", border: `1px solid ${color}44` }}
                            >
                                <div className="flex justify-center mb-2">
                                    {isHealthy
                                        ? <CheckCircle className="w-8 h-8 text-emerald-400" />
                                        : <AlertCircle className="w-8 h-8" style={{ color }} />}
                                </div>
                                <p className="font-bold text-white text-base">{label}</p>
                                <p className="text-sm mt-1" style={{ color }}>
                                    {(lastResult.confidence * 100).toFixed(1)}% confidence
                                </p>
                            </div>
                            <div className="space-y-1.5">
                                {Object.entries(lastResult.all_scores || {}).map(([c, v]) => (
                                    <div key={c} className="grid grid-cols-[minmax(72px,110px)_minmax(0,1fr)_36px] items-center gap-2">
                                        <div className="flex items-center gap-1.5 min-w-0">
                                            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: CLASS_COLORS[c] || "#94a3b8" }} />
                                            <span className="text-gray-400 text-xs truncate">{CLASS_LABELS[c] || c}</span>
                                        </div>
                                        <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                                            <div className="h-full rounded-full" style={{ width: `${v * 100}%`, background: CLASS_COLORS[c] || "#94a3b8" }} />
                                        </div>
                                        <span className="text-gray-500 text-xs w-10 text-right">{(v * 100).toFixed(0)}%</span>
                                    </div>
                                ))}
                            </div>
                            <p className="text-gray-600 text-xs text-center">
                                {new Date(lastResult.captured_at).toLocaleString("vi-VN")}
                            </p>
                            {advice && (
                                <div className="rounded-xl border border-gray-800 bg-gray-800/50 p-3">
                                    <p className="text-sm font-semibold text-white">{advice.status}</p>
                                    <p className="text-xs text-gray-400 mt-1 leading-relaxed">{advice.advice}</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

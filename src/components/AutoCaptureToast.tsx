"use client";
import Link from "next/link";
import { Camera, AlertCircle, CheckCircle, X } from "lucide-react";
import { useCapture } from "@/context/CaptureContext";
import { CLASS_LABELS, CLASS_COLORS } from "@/lib/api";
import { useState } from "react";

export default function AutoCaptureToast() {
    const { autoCapture, capturing, countdown, lastResult, intervalMin } = useCapture();
    const [dismissed, setDismissed] = useState(false);

    // Hiện khi bật auto hoặc vừa có kết quả mới, chưa bị dismiss
    if ((!autoCapture && !lastResult) || dismissed) return null;

    const cls = lastResult?.predicted_class;
    const color = cls ? CLASS_COLORS[cls] || "#94a3b8" : "#94a3b8";
    const label = cls ? CLASS_LABELS[cls] || cls : "";
    const isHealthy = cls === "Binh_thuong";

    const mm = String(Math.floor(countdown / 60)).padStart(2, "0");
    const ss = String(countdown % 60).padStart(2, "0");

    return (
        <div className="fixed inset-x-3 bottom-3 z-50 overflow-hidden rounded-2xl border border-gray-700 bg-gray-900 shadow-2xl shadow-black/50 sm:inset-x-auto sm:bottom-5 sm:right-5 sm:w-72">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${autoCapture ? "bg-emerald-400 animate-pulse" : "bg-gray-600"}`} />
                    <span className="text-sm font-medium text-white">Auto Camera</span>
                    {autoCapture && (
                        <span className="text-xs text-gray-400">(mỗi {intervalMin} phút)</span>
                    )}
                </div>
                <button
                    onClick={() => setDismissed(true)}
                    className="text-gray-600 hover:text-gray-400 transition"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Countdown */}
            {autoCapture && (
                <div className="px-4 py-2 bg-gray-800/60 flex items-center gap-3">
                    <Camera className={`w-4 h-4 ${capturing ? "text-blue-400 animate-pulse" : "text-gray-400"}`} />
                    <span className="text-xs text-gray-400 flex-1">
                        {capturing ? "Đang chụp & phân tích..." : `Chụp tiếp sau: ${mm}:${ss}`}
                    </span>
                    {/* compact progress */}
                    <div className="w-16 bg-gray-700 rounded-full h-1 overflow-hidden">
                        <div
                            className="h-full bg-emerald-500 transition-all duration-1000"
                            style={{ width: autoCapture ? `${(1 - countdown / (intervalMin * 60)) * 100}%` : "0%" }}
                        />
                    </div>
                </div>
            )}

            {/* Last result */}
            {lastResult && (
                <div className="px-4 py-3">
                    <p className="text-xs text-gray-500 mb-2">Kết quả lần cuối</p>
                    <div className="flex items-center gap-3">
                        {isHealthy
                            ? <CheckCircle className="w-7 h-7 text-emerald-400 flex-shrink-0" />
                            : <AlertCircle className="w-7 h-7 flex-shrink-0" style={{ color }} />}
                        <div>
                            <p className="font-semibold text-white text-sm">{label}</p>
                            <p className="text-xs" style={{ color }}>
                                {(lastResult.confidence * 100).toFixed(1)}% confidence
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Go to live */}
            <Link
                href="/live"
                className="block text-center text-xs text-gray-500 hover:text-gray-300 py-2 border-t border-gray-800 transition"
            >
                Xem Camera Live →
            </Link>
        </div>
    );
}

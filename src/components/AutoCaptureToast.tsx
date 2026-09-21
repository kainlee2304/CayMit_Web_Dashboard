"use client";
import Link from "next/link";
import { Camera, AlertCircle, CheckCircle, X } from "lucide-react";
import { useCapture } from "@/context/CaptureContext";
import { useLanguage } from "@/context/LanguageContext";
import { CLASS_LABELS, CLASS_COLORS } from "@/lib/api";
import { useState } from "react";

export default function AutoCaptureToast() {
    const { autoCapture, setAutoCapture, capturing, countdown, lastResult, intervalMin } = useCapture();
    const { t } = useLanguage();
    const [dismissed, setDismissed] = useState(false);

    if ((!autoCapture && !lastResult) || dismissed) return null;

    const cls = lastResult?.predicted_class;
    const color = cls ? CLASS_COLORS[cls] || "#94a3b8" : "#94a3b8";
    
    let displayLabel = "";
    if (cls === "not_jackfruit") {
        displayLabel = t.live.noFruitDetected;
    } else if (cls === "Binh_thuong" || cls === "healthy") {
        displayLabel = t.live.healthy;
    } else if (cls) {
        displayLabel = CLASS_LABELS[cls] || cls;
    }

    const isHealthy = cls === "Binh_thuong" || cls === "healthy";
    const mm = String(Math.floor(countdown / 60)).padStart(2, "0");
    const ss = String(countdown % 60).padStart(2, "0");

    return (
        <div className="fixed inset-x-3 bottom-3 z-50 overflow-hidden rounded-2xl border border-gray-700 bg-gray-900 shadow-2xl shadow-black/50 sm:inset-x-auto sm:bottom-5 sm:right-5 sm:w-72 font-sans">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${autoCapture ? "bg-emerald-400 animate-pulse" : "bg-gray-600"}`} />
                    <span className="text-sm font-medium text-white">Auto Camera</span>
                    {autoCapture && (
                        <span className="text-xs text-gray-400">({intervalMin} {t.live.minutes})</span>
                    )}
                </div>
                <div className="flex items-center gap-1.5">
                    {autoCapture && (
                        <button
                            onClick={() => setAutoCapture(false)}
                            className="text-xs text-rose-400 hover:text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded-md border border-rose-500/20 transition"
                            title={t.live.stopAuto}
                        >
                            {t.live.stopAuto}
                        </button>
                    )}
                    <button
                        onClick={() => setDismissed(true)}
                        className="text-gray-600 hover:text-gray-400 transition"
                        title={t.common.close}
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Countdown */}
            {autoCapture && (
                <div className="px-4 py-2 bg-gray-800/60 flex items-center gap-3">
                    <Camera className={`w-4 h-4 ${capturing ? "text-blue-400 animate-pulse" : "text-gray-400"}`} />
                    <span className="text-xs text-gray-400 flex-1 truncate">
                        {capturing ? t.live.capturing : `${t.live.nextCaptureIn}: ${mm}:${ss}`}
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
                    <p className="text-xs text-gray-500 mb-2">{t.live.resultTitle}</p>
                    <div className="flex items-center gap-3">
                        {isHealthy
                            ? <CheckCircle className="w-7 h-7 text-emerald-400 flex-shrink-0" />
                            : <AlertCircle className="w-7 h-7 flex-shrink-0" style={{ color }} />}
                        <div className="min-w-0">
                            <p className="font-semibold text-white text-sm truncate">{displayLabel}</p>
                            <p className="text-xs" style={{ color }}>
                                {(lastResult.confidence * 100).toFixed(1)}% {t.live.confidence}
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
                {t.live.title} →
            </Link>
        </div>
    );
}

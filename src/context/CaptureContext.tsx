"use client";
import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { captureFromCamera } from "@/lib/api";

type CaptureResult = {
    id: number;
    predicted_class: string;
    confidence: number;
    all_scores: Record<string, number>;
    model_used: string;
    image_filename?: string;
    captured_at: string;
};

type CaptureCtx = {
    selectedModel: string;
    setSelectedModel: (v: string) => void;
    autoCapture: boolean;
    setAutoCapture: (v: boolean) => void;
    intervalMin: number;
    setIntervalMin: (v: number) => void;
    capturing: boolean;
    countdown: number;
    lastResult: CaptureResult | null;
    doCapture: () => Promise<void>;
};

const CaptureContext = createContext<CaptureCtx | null>(null);

export function CaptureProvider({ children }: { children: React.ReactNode }) {
    const [selectedModel, setSelectedModel] = useState("best_11");
    const [autoCapture, setAutoCapture] = useState(false);
    const [intervalMin, setIntervalMin] = useState(1);
    const [capturing, setCapturing] = useState(false);
    const [lastResult, setLastResult] = useState<CaptureResult | null>(null);
    const [countdown, setCountdown] = useState(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const cdRef = useRef<NodeJS.Timeout | null>(null);

    const doCapture = useCallback(async () => {
        if (capturing) return;
        setCapturing(true);
        try {
            const res = await captureFromCamera(selectedModel);
            setLastResult(res);
        } catch (e) {
            console.error("[auto-capture]", e);
        } finally {
            setCapturing(false);
        }
    }, [capturing, selectedModel]);

    useEffect(() => {
        if (!autoCapture) {
            clearInterval(timerRef.current!);
            clearInterval(cdRef.current!);
            setCountdown(0);
            return;
        }

        const totalSec = intervalMin * 60;
        setCountdown(totalSec);

        // Chụp ngay lần đầu
        doCapture();

        // Countdown mỗi giây
        cdRef.current = setInterval(() => {
            setCountdown((c) => (c <= 1 ? totalSec : c - 1));
        }, 1000);

        // Chụp định kỳ
        timerRef.current = setInterval(doCapture, totalSec * 1000);

        return () => {
            clearInterval(timerRef.current!);
            clearInterval(cdRef.current!);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoCapture, intervalMin]);

    return (
        <CaptureContext.Provider
            value={{ selectedModel, setSelectedModel, autoCapture, setAutoCapture, intervalMin, setIntervalMin, capturing, countdown, lastResult, doCapture }}
        >
            {children}
        </CaptureContext.Provider>
    );
}

export function useCapture() {
    const ctx = useContext(CaptureContext);
    if (!ctx) throw new Error("useCapture must be used within CaptureProvider");
    return ctx;
}

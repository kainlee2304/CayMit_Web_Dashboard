"use client";
import { useEffect, useState, useCallback } from "react";
import useSWR from "swr";
import { Thermometer, Droplets, Cpu, CloudUpload, Power, RefreshCw, Camera } from "lucide-react";
import {
  getSummary, getLatestSensor, getPredictions, uploadPredict, setLight, captureFromCamera, getModels,
  CLASS_LABELS, CLASS_COLORS, Prediction, Summary, SensorData, ModelInfo,
  MODEL_LABELS, FALLBACK_MODELS, getOverallAdvice,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

// ─── Stat Card ─────────────────────────────────────────────────────────────
function StatCard({ label, value, unit, icon: Icon, color }: {
  label: string; value: string | number | null; unit?: string;
  icon: React.ElementType; color: string;
}) {
  return (
    <div className="min-w-0 rounded-2xl border border-gray-800 bg-gray-900 p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-400 text-sm">{label}</span>
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center`} style={{ background: color + "22" }}>
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
      </div>
      <p className="break-words text-2xl font-bold text-white sm:text-3xl">
        {value ?? "—"} <span className="text-lg font-normal text-gray-400">{unit}</span>
      </p>
    </div>
  );
}

// ─── Prediction Card ────────────────────────────────────────────────────────
function PredCard({ p }: { p: Prediction }) {
  const color = CLASS_COLORS[p.predicted_class] || "#94a3b8";
  const label = CLASS_LABELS[p.predicted_class] || p.predicted_class;
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex gap-4 items-start">
      {p.image_path && (
        <img
          src={`${API_URL}/uploads/${p.image_path.split(/[\\/]/).pop()}`}
          alt="capture"
          className="w-16 h-16 rounded-lg object-cover flex-shrink-0 border border-gray-700"
        />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
          <span className="font-semibold text-white truncate">{label}</span>
        </div>
        <p className="text-sm text-gray-400">
          Confidence: <span style={{ color }}>{(p.confidence * 100).toFixed(1)}%</span>
        </p>
        <p className="text-xs text-gray-600 mt-1">
          {new Date(p.created_at).toLocaleString("vi-VN")}
        </p>
      </div>
    </div>
  );
}

// ─── Main Dashboard Page ────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: summary, mutate: mutateSummary } = useSWR<Summary>("summary", getSummary, { refreshInterval: 15000 });
  const { data: sensor } = useSWR<SensorData>("sensor", getLatestSensor, { refreshInterval: 10000 });
  const { data: loadedModels } = useSWR<ModelInfo[]>("models", getModels);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [selectedModel, setSelectedModel] = useState("best_11");
  const [lightOn, setLightOn] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const modelOptions = loadedModels?.length ? loadedModels : FALLBACK_MODELS;
  const latestAdvice = getOverallAdvice(predictions[0]);

  // Load latest predictions
  const loadPredictions = useCallback(async () => {
    const data = await getPredictions({ limit: 6 });
    setPredictions(data);
  }, []);

  useEffect(() => { loadPredictions(); }, [loadPredictions]);

  // WebSocket real-time
  useEffect(() => {
    const defaultWsUrl = process.env.NODE_ENV === "production"
      ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`
      : "ws://localhost:8000/ws";
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL || defaultWsUrl);
    ws.onmessage = () => { loadPredictions(); mutateSummary(); };
    const ping = setInterval(() => ws.readyState === 1 && ws.send("ping"), 30000);
    return () => { clearInterval(ping); ws.close(); };
  }, [loadPredictions, mutateSummary]);

  // Upload predict
  const handleFile = async (file: File) => {
    setUploading(true);
    try {
      const result = await uploadPredict(file, selectedModel);
      setPredictions((prev) => [result, ...prev.slice(0, 5)]);
      mutateSummary();
    } catch (e) {
      console.error(e);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleCapture = async () => {
    setCapturing(true);
    try {
      await captureFromCamera(selectedModel);
      await loadPredictions();
      mutateSummary();
    } catch (e) {
      console.error(e);
    } finally {
      setCapturing(false);
    }
  };

  const toggleLight = async () => {
    const next = !lightOn;
    setLightOn(next);
    await setLight("jetson-nano-01", next);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">Hệ thống phát hiện bệnh cây Mít real-time</p>
        </div>
        <button onClick={() => { loadPredictions(); mutateSummary(); }}
          className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-gray-800 px-4 py-2 text-sm text-gray-300 transition hover:bg-gray-700 sm:w-auto">
          <RefreshCw className="w-4 h-4" /> Làm mới
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
        <StatCard label="Nhiệt Độ" value={sensor?.temperature ?? null} unit="°C" icon={Thermometer} color="#f87171" />
        <StatCard label="Độ Ẩm" value={sensor?.humidity ?? null} unit="%" icon={Droplets} color="#60a5fa" />
        <StatCard label="Tổng Phát Hiện" value={summary?.total_predictions ?? null} icon={Cpu} color="#a78bfa" />
        <div className="flex min-w-0 flex-col justify-between rounded-2xl border border-gray-800 bg-gray-900 p-4 sm:p-5">
          <span className="text-gray-400 text-sm">Hệ Thống Đèn</span>
          <div className="flex items-center justify-between mt-3">
            <span className={`text-lg font-bold ${lightOn ? "text-emerald-400" : "text-gray-500"}`}>
              {lightOn ? "BẬT" : "TẮT"}
            </span>
            <button onClick={toggleLight}
              className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${lightOn ? "bg-emerald-500 shadow-lg shadow-emerald-500/30" : "bg-gray-700 hover:bg-gray-600"
                }`}>
              <Power className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>
      </div>

      {/* Disease Breakdown */}
      {summary?.class_breakdown && (
        <div className="min-w-0 rounded-2xl border border-gray-800 bg-gray-900 p-4 sm:p-5">
          <h2 className="text-white font-semibold mb-4">Phân Loại Bệnh</h2>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {Object.entries(summary.class_breakdown).map(([cls, count]) => (
              <div key={cls} className="min-w-0 rounded-xl bg-gray-800 p-3 text-center sm:p-4">
                <div className="w-3 h-3 rounded-full mx-auto mb-2" style={{ background: CLASS_COLORS[cls] || "#94a3b8" }} />
                <p className="text-2xl font-bold text-white">{count}</p>
                <p className="text-xs text-gray-400 mt-1 leading-tight">{CLASS_LABELS[cls] || cls}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid min-w-0 gap-5 lg:grid-cols-2 lg:gap-6">
        {/* Upload & Predict */}
        <div className="min-w-0 rounded-2xl border border-gray-800 bg-gray-900 p-4 sm:p-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-white font-semibold">Phân Tích Ảnh</h2>
            <button
              onClick={handleCapture}
              disabled={capturing}
              className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-blue-500/40 bg-blue-500/20 px-4 py-2 text-sm font-medium text-blue-400 transition hover:bg-blue-500/30 disabled:opacity-50 sm:w-auto"
            >
              {capturing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Camera className="w-4 h-4" />}
              {capturing ? "Đang chụp..." : "Chụp Từ Camera"}
            </button>
          </div>
          <div className="mb-4">
            <label className="text-gray-500 text-xs mb-1.5 block">Chọn model phân tích</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white outline-none focus:border-emerald-500"
            >
              {modelOptions.map((model) => (
                <option key={model.name} value={model.name}>
                  {MODEL_LABELS[model.name] || model.name}
                </option>
              ))}
            </select>
          </div>
          <label
            className={`flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-xl cursor-pointer transition-all ${isDragging ? "border-emerald-500 bg-emerald-500/5" : "border-gray-700 hover:border-gray-500 bg-gray-800/50"
              }`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
          >
            <input type="file" className="hidden" accept="image/*"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
            {uploading ? (
              <div className="flex items-center gap-2 text-emerald-400">
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Đang phân tích...</span>
              </div>
            ) : (
              <>
                <CloudUpload className="w-10 h-10 text-gray-500 mb-2" />
                <p className="text-gray-400 text-sm">Kéo thả hoặc click để chọn ảnh</p>
                <p className="text-gray-600 text-xs mt-1">JPG, PNG, WEBP</p>
              </>
            )}
          </label>
          {latestAdvice && (
            <div className="mt-4 rounded-xl border border-gray-800 bg-gray-800/50 p-4">
              <p className="text-sm font-semibold text-white">{latestAdvice.status}</p>
              <p className="text-xs text-gray-400 mt-1 leading-relaxed">{latestAdvice.advice}</p>
            </div>
          )}
        </div>

        {/* Latest Predictions Feed */}
        <div className="min-w-0 rounded-2xl border border-gray-800 bg-gray-900 p-4 sm:p-5">
          <h2 className="text-white font-semibold mb-4">Kết Quả Gần Đây</h2>
          <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
            {predictions.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-8">Chưa có dữ liệu</p>
            ) : (
              predictions.map((p) => <PredCard key={p.id} p={p} />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";
import useSWR from "swr";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
    LineChart, Line, CartesianGrid,
} from "recharts";
import { useLanguage } from "@/context/LanguageContext";
import { getSummary, getDiseaseChart, getSensorChart, CLASS_LABELS, CLASS_COLORS } from "@/lib/api";

type DiseaseChartData = {
    data: Record<string, Record<string, number>>;
};

type SensorChartItem = {
    time: string;
    temperature: number;
    humidity: number;
};

type SensorChartData = {
    data: SensorChartItem[];
};

export default function StatsPage() {
    const { t, language } = useLanguage();
    const { data: summary } = useSWR("summary", getSummary, { refreshInterval: 30000 });
    const { data: diseaseChart } = useSWR<DiseaseChartData>("disease-chart", () => getDiseaseChart(7), { refreshInterval: 30000 });
    const { data: sensorChart } = useSWR<SensorChartData>("sensor-chart", () => getSensorChart(24), { refreshInterval: 30000 });

    const diseaseData = diseaseChart?.data
        ? Object.entries(diseaseChart.data).map(([date, counts]) => ({
            date,
            ...counts,
        }))
        : [];

    const sensorData = sensorChart?.data?.map((item) => {
        const d = new Date(item.time);
        const timeStr = isNaN(d.getTime()) ? "—" : d.toLocaleTimeString(language === "en" ? "en-US" : "vi-VN", { hour: "2-digit", minute: "2-digit" });
        return {
            time: timeStr,
            temperature: item.temperature,
            humidity: item.humidity,
        };
    }) || [];

    const classData = summary?.class_breakdown
        ? Object.entries(summary.class_breakdown).map(([cls, count]) => ({
            name: CLASS_LABELS[cls] || cls,
            count,
            color: CLASS_COLORS[cls] || "#94a3b8",
        }))
        : [];

    return (
        <div className="mx-auto w-full max-w-7xl space-y-5 sm:space-y-6 font-sans">
            <div>
                <h1 className="text-2xl font-bold text-white">{t.stats.title}</h1>
                <p className="text-gray-500 text-sm mt-0.5">{t.stats.subtitle}</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4">
                {classData.map((item) => (
                    <div key={item.name} className="min-w-0 rounded-2xl border border-gray-800 bg-gray-900 p-4 sm:p-5">
                        <div className="w-3 h-3 rounded-full mb-3" style={{ background: item.color }} />
                        <p className="text-3xl font-bold text-white">{item.count}</p>
                        <p className="text-gray-400 text-sm mt-1 leading-tight">{item.name}</p>
                    </div>
                ))}
            </div>

            {/* Disease Chart (7 days) */}
            <div className="min-w-0 overflow-hidden rounded-2xl border border-gray-800 bg-gray-900 p-3 sm:p-5">
                <h2 className="text-white font-semibold mb-4">{t.stats.diseaseBreakdown} (7 {language === "en" ? "days" : "ngày"})</h2>
                {diseaseData.length === 0 ? (
                    <div className="flex items-center justify-center h-48 text-gray-500 text-sm">{t.common.noData}</div>
                ) : (
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={diseaseData} barGap={4}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                            <XAxis dataKey="date" stroke="#6b7280" tick={{ fontSize: 11 }} />
                            <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} />
                            <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
                                labelStyle={{ color: "#fff" }} itemStyle={{ color: "#94a3b8" }} />
                            <Legend iconType="circle" iconSize={8} />
                            {Object.keys(CLASS_COLORS).map((cls) => (
                                <Bar key={cls} dataKey={cls} name={CLASS_LABELS[cls] || cls}
                                    fill={CLASS_COLORS[cls]} radius={[4, 4, 0, 0]} />
                            ))}
                        </BarChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* Sensor Chart (24h) */}
            <div className="min-w-0 overflow-hidden rounded-2xl border border-gray-800 bg-gray-900 p-3 sm:p-5">
                <h2 className="text-white font-semibold mb-4">{t.stats.sensorReadings} (24 {language === "en" ? "hours" : "giờ"})</h2>
                {sensorData.length === 0 ? (
                    <div className="flex items-center justify-center h-48 text-gray-500 text-sm">{t.common.noData}</div>
                ) : (
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={sensorData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                            <XAxis dataKey="time" stroke="#6b7280" tick={{ fontSize: 10 }} />
                            <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} />
                            <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", borderRadius: 8 }}
                                labelStyle={{ color: "#fff" }} />
                            <Legend iconType="circle" iconSize={8} />
                            <Line type="monotone" dataKey="temperature" name={`${t.stats.temperature} (°C)`}
                                stroke="#f87171" dot={false} strokeWidth={2} />
                            <Line type="monotone" dataKey="humidity" name={`${t.stats.humidity} (%)`}
                                stroke="#60a5fa" dot={false} strokeWidth={2} />
                        </LineChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}

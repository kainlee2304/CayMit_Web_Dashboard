"use client";

import React, { useState, useEffect } from "react";
import {
  getSeasons,
  createSeason,
  closeSeason,
  getPlots,
  CropSeason,
  Plot,
} from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import {
  CalendarRange,
  Plus,
  Search,
  RefreshCw,
  Sprout,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  TrendingUp,
  MapPin,
  X,
  Layers,
  Lock,
} from "lucide-react";
import Link from "next/link";

export default function SeasonsPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const [seasons, setSeasons] = useState<CropSeason[]>([]);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [closingId, setClosingId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Form State
  const [form, setForm] = useState({
    plot_id: "",
    season_name: "",
    start_date: new Date().toISOString().split("T")[0],
    expected_harvest_start: new Date(Date.now() + 90 * 86400000).toISOString().split("T")[0],
    expected_harvest_end: new Date(Date.now() + 150 * 86400000).toISOString().split("T")[0],
    forecasted_yield_kg: 8500,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [seasonsData, plotsData] = await Promise.all([
        getSeasons(statusFilter !== "ALL" ? { season_status: statusFilter } : undefined),
        getPlots(),
      ]);
      setSeasons(seasonsData);
      setPlots(plotsData);
      if (plotsData.length > 0 && !form.plot_id) {
        setForm((prev) => ({
          ...prev,
          plot_id: plotsData[0].id,
          season_name: `Vụ Mít ${plotsData[0].plot_name} ${new Date().getFullYear()}`,
        }));
      }
    } catch (err: any) {
      console.error("Failed to load seasons:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const selectedPlot = plots.find((p) => p.id === form.plot_id);

  const handlePlotChange = (plotId: string) => {
    const plot = plots.find((p) => p.id === plotId);
    setForm((prev) => ({
      ...prev,
      plot_id: plotId,
      season_name: plot ? `Vụ Mít ${plot.plot_name} ${new Date().getFullYear()}` : prev.season_name,
    }));
  };

  const handleCreateSeason = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setMessage(null);
    try {
      await createSeason({
        plot_id: form.plot_id,
        season_name: form.season_name,
        start_date: form.start_date,
        expected_harvest_start: form.expected_harvest_start,
        expected_harvest_end: form.expected_harvest_end,
        forecasted_yield_kg: Number(form.forecasted_yield_kg),
      });
      setMessage({ type: "success", text: language === "vi" ? "Khởi tạo mùa vụ mới thành công!" : "Season created successfully!" });
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      const errDetail = err.response?.data?.error?.message || err.message || "Failed to create season";
      setMessage({ type: "error", text: errDetail });
    } finally {
      setCreating(false);
    }
  };

  const handleCloseSeason = async (seasonId: string) => {
    if (!window.confirm(t.seasons.closeSeasonConfirm)) return;
    try {
      setClosingId(seasonId);
      await closeSeason(seasonId, "Closed by farm manager");
      setMessage({ type: "success", text: language === "vi" ? "Đã đóng mùa vụ thành công." : "Season closed successfully." });
      loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.error?.message || "Failed to close season" });
    } finally {
      setClosingId(null);
    }
  };

  // KPI Calculations
  const totalSeasons = seasons.length;
  const activeSeasons = seasons.filter((s) => s.season_status === "ACTIVE" || s.season_status === "HARVESTING").length;
  const totalForecastKg = seasons.reduce((sum, s) => sum + (s.forecasted_yield_kg || 0), 0);
  const verifiedVarietyCount = seasons.filter((s) => s.is_variety_verified).length;

  const filteredSeasons = seasons.filter((s) => {
    const matchesSearch =
      s.season_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.season_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.plot_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.inherited_variety_name_vi || "").toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />{t.seasons.statusActive}</span>;
      case "HARVESTING":
        return <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-400 border border-amber-500/20"><span className="h-1.5 w-1.5 rounded-full bg-amber-400" />{t.seasons.statusHarvesting}</span>;
      case "CLOSED":
        return <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-700/50 px-2.5 py-1 text-xs font-semibold text-gray-400 border border-gray-600/30"><Lock className="h-3 w-3" />{t.seasons.statusClosed}</span>;
      case "CANCELLED":
        return <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-1 text-xs font-semibold text-rose-400 border border-rose-500/20">{t.seasons.statusCancelled}</span>;
      default:
        return <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2.5 py-1 text-xs font-semibold text-blue-400 border border-blue-500/20">{status}</span>;
    }
  };

  const canCreate = user?.role === "admin_hq" || user?.role === "admin" || user?.role === "farmer" || user?.role === "producer";

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <CalendarRange className="h-7 w-7 text-emerald-400" />
            {t.seasons.title}
          </h1>
          <p className="text-sm text-gray-400 mt-1">{t.seasons.subtitle}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-gray-700 bg-gray-800/80 px-4 py-2.5 text-xs font-semibold text-gray-200 hover:bg-gray-700 hover:text-white transition disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-emerald-400" : ""}`} />
            {t.common.refresh}
          </button>
          {canCreate && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 transition"
            >
              <Plus className="h-4 w-4" />
              {t.seasons.addSeason}
            </button>
          )}
        </div>
      </div>

      {/* Alert Notification */}
      {message && (
        <div
          className={`flex items-center justify-between rounded-xl p-4 text-xs font-medium border ${
            message.type === "success"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="text-gray-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* KPI Cards Banner */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">{t.seasons.title}</span>
            <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-400 border border-emerald-500/20">
              <CalendarRange className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-3 text-2xl font-black text-white">{totalSeasons}</p>
          <p className="text-[11px] text-gray-500 mt-1">{t.seasons.activeSeasonsCount}: {activeSeasons}</p>
        </div>

        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">{t.seasons.statusActive}</span>
            <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-3 text-2xl font-black text-emerald-400">{activeSeasons}</p>
          <p className="text-[11px] text-gray-500 mt-1">{totalSeasons > 0 ? `${Math.round((activeSeasons / totalSeasons) * 100)}%` : "0%"} {t.seasons.statusActive.toLowerCase()}</p>
        </div>

        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">{t.seasons.forecastedYield}</span>
            <div className="rounded-xl bg-amber-500/10 p-2 text-amber-400 border border-amber-500/20">
              <TrendingUp className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-3 text-2xl font-black text-white">
            {totalForecastKg >= 1000 ? `${(totalForecastKg / 1000).toFixed(1)} tấn` : `${totalForecastKg.toLocaleString()} kg`}
          </p>
          <p className="text-[11px] text-gray-500 mt-1">{t.seasons.totalForecastKg}</p>
        </div>

        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">{t.common.trustHeader}</span>
            <div className="rounded-xl bg-indigo-500/10 p-2 text-indigo-400 border border-indigo-500/20">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-3 text-2xl font-black text-indigo-400">{verifiedVarietyCount} / {totalSeasons}</p>
          <p className="text-[11px] text-gray-500 mt-1">{t.common.level2Count}</p>
        </div>
      </div>

      {/* Search & Status Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder={t.common.search}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-xl border border-gray-800 bg-gray-900/80 py-2.5 pl-10 pr-4 text-xs text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto p-1 rounded-xl bg-gray-900/80 border border-gray-800">
          {["ALL", "ACTIVE", "HARVESTING", "CLOSED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                statusFilter === st
                  ? "bg-emerald-600 text-white font-semibold shadow-sm"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {st === "ALL" ? t.common.filter + ": " + (language === "vi" ? "Tất cả" : "All") : t.seasons[`status${st.charAt(0) + st.slice(1).toLowerCase()}` as keyof typeof t.seasons] || st}
            </button>
          ))}
        </div>
      </div>

      {/* Seasons Grid / Cards */}
      {loading ? (
        <div className="flex min-h-64 items-center justify-center rounded-2xl border border-gray-800 bg-gray-900/40">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="h-8 w-8 animate-spin text-emerald-500" />
            <span className="text-xs text-gray-400">{t.common.loading}</span>
          </div>
        </div>
      ) : filteredSeasons.length === 0 ? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-2xl border border-gray-800 bg-gray-900/40 p-8 text-center">
          <CalendarRange className="h-12 w-12 text-gray-600 mb-3" />
          <p className="text-sm font-semibold text-gray-300">{t.common.noData}</p>
          <p className="text-xs text-gray-500 mt-1 max-w-sm">
            {language === "vi" ? "Chưa có mùa vụ nào được tạo hoặc không khớp với bộ lọc." : "No crop seasons found matching your search criteria."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filteredSeasons.map((season) => {
            const varietyName = language === "vi" ? (season.inherited_variety_name_vi || season.inherited_variety_code) : (season.inherited_variety_name_en || season.inherited_variety_code);
            return (
              <div
                key={season.id}
                className="group relative flex flex-col justify-between rounded-2xl border border-gray-800 bg-gray-900/70 p-5 hover:border-emerald-500/40 hover:bg-gray-900/90 transition-all shadow-lg shadow-black/20"
              >
                <div>
                  {/* Top Bar inside card */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                        {season.season_code}
                      </span>
                      <h3 className="text-base font-bold text-white mt-1.5 group-hover:text-emerald-300 transition">
                        {season.season_name}
                      </h3>
                    </div>
                    <div>{getStatusBadge(season.season_status)}</div>
                  </div>

                  {/* Plot and Farm Information */}
                  <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
                    <span className="flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-emerald-400" />
                      {season.plot_name || "Thửa Đất"}
                    </span>
                    {season.farm_name && (
                      <span className="flex items-center gap-1.5">
                        <MapPin className="h-3.5 w-3.5 text-gray-500" />
                        {season.farm_name}
                      </span>
                    )}
                  </div>

                  {/* Inherited Upstream Variety Badge */}
                  <div className="mt-3.5 rounded-xl border border-gray-800 bg-gray-950/60 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-medium text-gray-400 flex items-center gap-1.5">
                        <Sprout className="h-3.5 w-3.5 text-emerald-400" />
                        {t.seasons.variety}:
                      </span>
                      {season.is_variety_verified ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          <ShieldCheck className="h-3 w-3" />
                          {t.seasons.varietyVerifiedBadge}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                          <AlertCircle className="h-3 w-3" />
                          {t.seasons.varietyDeclaredBadge}
                        </span>
                      )}
                    </div>
                    <p className="text-xs font-bold text-white mt-1">{varietyName || "Mít Thái Changai"}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">{t.seasons.inheritedFromClaim}</p>
                  </div>

                  {/* Dates & Yield metrics */}
                  <div className="mt-4 grid grid-cols-2 gap-3 pt-3 border-t border-gray-800/80 text-xs">
                    <div>
                      <span className="text-[11px] text-gray-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {t.seasons.startDate}
                      </span>
                      <p className="font-semibold text-gray-200 mt-0.5">{season.start_date}</p>
                    </div>

                    <div>
                      <span className="text-[11px] text-gray-500 flex items-center gap-1">
                        <CalendarRange className="h-3 w-3" />
                        {t.seasons.harvestWindow}
                      </span>
                      <p className="font-semibold text-amber-300 mt-0.5">
                        {season.expected_harvest_start} → {season.expected_harvest_end}
                      </p>
                    </div>

                    <div>
                      <span className="text-[11px] text-gray-500">{t.seasons.forecastedYield}</span>
                      <p className="font-bold text-white mt-0.5">
                        {season.forecasted_yield_kg ? `${season.forecasted_yield_kg.toLocaleString()} kg` : "—"}
                      </p>
                    </div>

                    <div>
                      <span className="text-[11px] text-gray-500">{t.seasons.activitiesCount}</span>
                      <p className="font-bold text-emerald-400 mt-0.5">
                        {season.activities_count ?? 0} {language === "vi" ? "lần ghi nhật ký" : "records"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Card Actions Footer */}
                <div className="mt-5 flex items-center justify-between border-t border-gray-800 pt-3">
                  <div className="flex items-center gap-2">
                    {season.season_status === "ACTIVE" && canCreate && (
                      <button
                        onClick={() => handleCloseSeason(season.id)}
                        disabled={closingId === season.id}
                        className="rounded-lg border border-gray-700 bg-gray-800/80 px-2.5 py-1.5 text-[11px] font-medium text-gray-300 hover:bg-gray-700 hover:text-rose-400 transition disabled:opacity-50"
                      >
                        {closingId === season.id ? (
                          <RefreshCw className="h-3 w-3 animate-spin inline mr-1" />
                        ) : (
                          <Lock className="h-3 w-3 inline mr-1" />
                        )}
                        {t.seasons.closeSeason}
                      </button>
                    )}
                  </div>

                  <Link
                    href={`/seasons/${season.id}`}
                    className="flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition"
                  >
                    {t.common.viewDetails}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Season Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-400 border border-emerald-500/20">
                  <CalendarRange className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{t.seasons.addSeason}</h3>
                  <p className="text-xs text-gray-400 mt-0.5">{t.seasons.subtitle}</p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSeason} className="mt-4 space-y-4">
              {/* Plot Selector */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  {t.seasons.plot} *
                </label>
                <select
                  value={form.plot_id}
                  onChange={(e) => handlePlotChange(e.target.value)}
                  required
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2.5 text-xs text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                >
                  {plots.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.plot_code} - {p.plot_name} ({p.farm_name || "Trang Trại"})
                    </option>
                  ))}
                </select>
              </div>

              {/* Upstream Variety Preview */}
              {selectedPlot && (
                <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3">
                  <span className="text-[11px] font-medium text-gray-400">{t.seasons.inheritedFromClaim}:</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs font-bold text-emerald-400">
                      {selectedPlot.tree_groups?.[0]?.variety_name || "Mít Thái Changai (Tự động kế thừa)"}
                    </span>
                    <span className="text-[10px] text-gray-500">Mã thửa: {selectedPlot.plot_code}</span>
                  </div>
                </div>
              )}

              {/* Season Name */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  {t.seasons.seasonName} *
                </label>
                <input
                  type="text"
                  value={form.season_name}
                  onChange={(e) => setForm({ ...form, season_name: e.target.value })}
                  required
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              {/* Date Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1.5">
                    {t.seasons.startDate} *
                  </label>
                  <input
                    type="date"
                    value={form.start_date}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                    required
                    className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1.5">
                    {t.seasons.harvestStart} *
                  </label>
                  <input
                    type="date"
                    value={form.expected_harvest_start}
                    onChange={(e) => setForm({ ...form, expected_harvest_start: e.target.value })}
                    required
                    className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1.5">
                    {t.seasons.harvestEnd} *
                  </label>
                  <input
                    type="date"
                    value={form.expected_harvest_end}
                    onChange={(e) => setForm({ ...form, expected_harvest_end: e.target.value })}
                    required
                    className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>

              {/* Yield Forecast */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  {t.seasons.forecastedYield} *
                </label>
                <input
                  type="number"
                  step="50"
                  min="100"
                  value={form.forecasted_yield_kg}
                  onChange={(e) => setForm({ ...form, forecasted_yield_kg: Number(e.target.value) })}
                  required
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              {/* Modal Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl border border-gray-700 bg-gray-800 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-700"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                >
                  {creating && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  {t.seasons.addSeason}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

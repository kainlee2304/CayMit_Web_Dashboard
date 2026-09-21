"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getSeasonById,
  closeSeason,
  SeasonDetail,
} from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import {
  CalendarRange,
  ArrowLeft,
  RefreshCw,
  Sprout,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  TrendingUp,
  MapPin,
  Layers,
  Lock,
  Plus,
  FileText,
  FlaskConical,
  Activity,
  AlertTriangle,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";

export default function SeasonDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const seasonId = params.id as string;

  const [season, setSeason] = useState<SeasonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"OVERVIEW" | "DIARY" | "MATERIALS" | "YIELD">("OVERVIEW");
  const [closing, setClosing] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getSeasonById(seasonId);
      setSeason(data);
    } catch (err: any) {
      console.error("Failed to load season details:", err);
      setMessage({ type: "error", text: err.response?.data?.error?.message || "Season not found" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (seasonId) {
      loadData();
    }
  }, [seasonId]);

  const handleCloseSeason = async () => {
    if (!window.confirm(t.seasons.closeSeasonConfirm)) return;
    try {
      setClosing(true);
      await closeSeason(seasonId, "Closed by authorized actor");
      setMessage({ type: "success", text: language === "vi" ? "Đã đóng mùa vụ thành công!" : "Season closed successfully!" });
      loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.error?.message || "Failed to close season" });
    } finally {
      setClosing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-emerald-500" />
          <span className="text-xs text-gray-400">{t.common.loading}</span>
        </div>
      </div>
    );
  }

  if (!season) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
        <AlertCircle className="h-12 w-12 text-rose-500 mb-3" />
        <h2 className="text-lg font-bold text-white">Không tìm thấy thông tin mùa vụ</h2>
        <p className="text-xs text-gray-400 mt-1">Mùa vụ không tồn tại hoặc bạn không có quyền truy cập dữ liệu này.</p>
        <Link
          href="/seasons"
          className="mt-4 flex items-center gap-2 rounded-xl bg-gray-800 px-4 py-2 text-xs font-semibold text-gray-200 hover:bg-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          {t.common.back}
        </Link>
      </div>
    );
  }

  const varietyName = language === "vi"
    ? (season.inherited_variety_name_vi || season.inherited_variety_code)
    : (season.inherited_variety_name_en || season.inherited_variety_code);

  const canManage = user?.role === "admin_hq" || user?.role === "admin" || user?.role === "farmer" || user?.role === "producer";

  return (
    <div className="space-y-6">
      {/* Top Header & Navigation */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-800 pb-5">
        <div className="flex items-center gap-3">
          <Link
            href="/seasons"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-800 bg-gray-900/80 text-gray-400 hover:bg-gray-800 hover:text-white transition"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                {season.season_code}
              </span>
              <span className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                season.season_status === "ACTIVE"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-gray-800 text-gray-400 border border-gray-700"
              }`}>
                {season.season_status === "ACTIVE" ? <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse mr-1" /> : null}
                {t.seasons[`status${season.season_status.charAt(0) + season.season_status.slice(1).toLowerCase()}` as keyof typeof t.seasons] || season.season_status}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
              {season.season_name}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/farm-diary?season_id=${season.id}`}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 transition"
          >
            <Plus className="h-4 w-4" />
            {t.farmDiary.addActivity}
          </Link>

          {season.season_status === "ACTIVE" && canManage && (
            <button
              onClick={handleCloseSeason}
              disabled={closing}
              className="flex items-center gap-2 rounded-xl border border-gray-700 bg-gray-800/80 px-4 py-2.5 text-xs font-semibold text-gray-300 hover:bg-gray-700 hover:text-rose-400 transition disabled:opacity-50"
            >
              {closing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
              {t.seasons.closeSeason}
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

      {/* Top Meta Summary Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Plot & Farm */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <span className="text-xs font-medium text-gray-400">{t.seasons.plot}</span>
          <p className="mt-2 text-base font-bold text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-emerald-400" />
            {season.plot_name}
          </p>
          <p className="text-[11px] text-gray-500 mt-1 flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {season.farm_name || "Nông trại HTX Tam Mỹ"}
          </p>
        </div>

        {/* Inherited Upstream Variety */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">{t.seasons.variety}</span>
            {season.is_variety_verified ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                <ShieldCheck className="h-3 w-3" />
                L2 Verified
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                <AlertCircle className="h-3 w-3" />
                L0 Declared
              </span>
            )}
          </div>
          <p className="mt-2 text-base font-bold text-emerald-400 flex items-center gap-2">
            <Sprout className="h-4 w-4 text-emerald-400" />
            {varietyName || "Mít Thái Changai"}
          </p>
          <p className="text-[11px] text-gray-500 mt-1">{t.seasons.inheritedFromClaim}</p>
        </div>

        {/* Expected Harvest Window */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <span className="text-xs font-medium text-gray-400">{t.seasons.harvestWindow}</span>
          <p className="mt-2 text-base font-bold text-amber-300 flex items-center gap-2">
            <CalendarRange className="h-4 w-4 text-amber-400" />
            {season.expected_harvest_start}
          </p>
          <p className="text-[11px] text-gray-500 mt-1">Đến ngày {season.expected_harvest_end}</p>
        </div>

        {/* Safe Harvest PHI status */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">{t.seasons.safeHarvestDate}</span>
            <FlaskConical className="h-4 w-4 text-emerald-400" />
          </div>
          <p className={`mt-2 text-base font-bold flex items-center gap-2 ${
            season.materials_summary?.is_safe_to_harvest ? "text-emerald-400" : "text-amber-400"
          }`}>
            {season.materials_summary?.is_safe_to_harvest ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-amber-400" />
            )}
            {season.materials_summary?.earliest_safe_harvest_date || season.start_date}
          </p>
          <p className="text-[11px] text-gray-500 mt-1">
            {season.materials_summary?.is_safe_to_harvest ? t.seasons.safeToHarvest : t.seasons.notSafeYet}
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-800 overflow-x-auto">
        <button
          onClick={() => setActiveTab("OVERVIEW")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition ${
            activeTab === "OVERVIEW"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <FileText className="h-4 w-4" />
          {t.seasons.detailsTabOverview}
        </button>

        <button
          onClick={() => setActiveTab("DIARY")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition ${
            activeTab === "DIARY"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Activity className="h-4 w-4" />
          {t.seasons.detailsTabDiary} ({season.farm_activities?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab("MATERIALS")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition ${
            activeTab === "MATERIALS"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <FlaskConical className="h-4 w-4" />
          {t.seasons.detailsTabMaterials} ({season.materials_summary?.total_applications || 0})
        </button>

        <button
          onClick={() => setActiveTab("YIELD")}
          className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold transition ${
            activeTab === "YIELD"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <TrendingUp className="h-4 w-4" />
          {t.seasons.detailsTabYield}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "OVERVIEW" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Production Progress Card */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <CalendarRange className="h-4 w-4 text-emerald-400" />
              Tiến Độ Chu Kỳ Mùa Vụ
            </h3>
            <div className="mt-4 space-y-4">
              <div>
                <div className="flex justify-between text-xs text-gray-400 mb-1.5">
                  <span>Ngày bắt đầu vụ: <b className="text-gray-200">{season.start_date}</b></span>
                  <span>Cửa sổ thu hoạch: <b className="text-amber-300">{season.expected_harvest_start}</b></span>
                </div>
                <div className="h-2 w-full rounded-full bg-gray-800 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-amber-400 rounded-full w-[65%]" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-800 text-xs">
                <div>
                  <span className="text-gray-500">{t.seasons.forecastedYield}</span>
                  <p className="text-base font-bold text-white mt-1">
                    {season.forecasted_yield_kg.toLocaleString()} kg
                  </p>
                </div>
                <div>
                  <span className="text-gray-500">{t.seasons.actualYield}</span>
                  <p className="text-base font-bold text-emerald-400 mt-1">
                    {season.actual_harvested_yield_kg ? `${season.actual_harvested_yield_kg.toLocaleString()} kg` : "0 kg (Đang nuôi trái)"}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Upstream Inheritance & Assurance */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-indigo-400" />
              {t.common.trustHeader}
            </h3>
            <p className="text-xs text-gray-400 mt-2 leading-relaxed">
              Mùa vụ này được liên kết trực tiếp với Thửa đất <b>{season.plot_name}</b> và kế thừa giống cây trồng từ bảo chứng nông nghiệp cấp tổ chức.
            </p>

            <div className="mt-4 rounded-xl border border-gray-800 bg-gray-950/70 p-4 space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Mã giống Master:</span>
                <span className="font-mono text-emerald-400 font-bold">{season.inherited_variety_code}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Tên thương phẩm:</span>
                <span className="text-white font-bold">{varietyName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Mức độ bảo chứng:</span>
                <span className="text-indigo-400 font-bold">{season.variety_assurance_level || "LEVEL_0_DECLARED"}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "DIARY" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">{t.farmDiary.title}</h3>
            <Link
              href={`/farm-diary?season_id=${season.id}`}
              className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300"
            >
              <Plus className="h-4 w-4" />
              {t.farmDiary.addActivity}
            </Link>
          </div>

          {season.farm_activities.length === 0 ? (
            <div className="flex min-h-48 flex-col items-center justify-center rounded-2xl border border-gray-800 bg-gray-900/40 p-8 text-center">
              <Activity className="h-10 w-10 text-gray-600 mb-2" />
              <p className="text-xs font-medium text-gray-400">{t.common.noData}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {season.farm_activities.map((act) => (
                <div
                  key={act.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-gray-800 bg-gray-900/70 p-4 hover:border-gray-700 transition"
                >
                  <div className="flex items-start gap-3.5">
                    <div className="rounded-xl bg-emerald-500/10 p-2.5 text-emerald-400 border border-emerald-500/20">
                      <Sprout className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-emerald-400">{act.activity_code}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          act.verification_status === "VERIFIED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>
                          {act.verification_status}
                        </span>
                        {act.is_geofence_verified && (
                          <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Geofenced
                          </span>
                        )}
                      </div>
                      <h4 className="text-sm font-bold text-white mt-1">
                        {act.activity_name_vi || act.activity_type_code}
                      </h4>
                      <p className="text-xs text-gray-400 mt-0.5">{act.notes || "Ghi chép hoạt động canh tác"}</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-4 text-xs text-gray-400">
                    <div>
                      <p className="text-gray-500 text-[11px]">Người thực hiện</p>
                      <p className="font-medium text-gray-200">{act.performed_by_name || "Nông hộ Ba Tám"}</p>
                    </div>
                    <Link
                      href={`/farm-diary/${act.id}`}
                      className="rounded-xl border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs font-semibold text-emerald-400 hover:bg-gray-700"
                    >
                      {t.common.details}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "MATERIALS" && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-emerald-400" />
              Tổng Hợp Vật Tư & Thời Gian Cách Ly (PHI Safe Harvest Timeline)
            </h3>
            <p className="text-xs text-gray-400 mt-1">
              Hệ thống tự động tính toán ngày thu hoạch an toàn nhất dựa trên tất cả các đợt bón phân và phun chế phẩm sinh học.
            </p>

            {/* PHI Status Banner */}
            <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-6 w-6 text-emerald-400" />
                <div>
                  <p className="text-xs font-bold text-white">Ngày sớm nhất được phép thu hoạch an toàn:</p>
                  <p className="text-base font-black text-emerald-400 mt-0.5">
                    {season.materials_summary?.earliest_safe_harvest_date || season.start_date}
                  </p>
                </div>
              </div>
              <span className="text-xs font-bold text-emerald-400 bg-emerald-500/20 px-3 py-1 rounded-full">
                {season.materials_summary?.is_safe_to_harvest ? "Đạt Tiêu Chuẩn PHI" : "Đang Cách Ly"}
              </span>
            </div>
          </div>
        </div>
      )}

      {activeTab === "YIELD" && (
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-amber-400" />
            Lịch Sử Khảo Sát & Ước Lượng Sản Lượng
          </h3>

          {!season.yield_estimates || season.yield_estimates.length === 0 ? (
            <p className="text-xs text-gray-400">Chưa có khảo sát ước lượng sản lượng độc lập.</p>
          ) : (
            <div className="space-y-3">
              {season.yield_estimates.map((ye) => (
                <div key={ye.id} className="rounded-xl border border-gray-800 bg-gray-950/70 p-4 text-xs">
                  <div className="flex justify-between font-semibold text-white">
                    <span>Phương pháp: {ye.estimation_method}</span>
                    <span className="text-amber-400 font-bold">{ye.estimated_yield_kg.toLocaleString()} kg</span>
                  </div>
                  <p className="text-gray-400 mt-1">{ye.notes}</p>
                  <div className="mt-2 flex justify-between text-[11px] text-gray-500">
                    <span>Người ước lượng: {ye.estimated_by_name || "Kỹ thuật viên"}</span>
                    <span>Độ tin cậy: {ye.confidence_level_pct}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

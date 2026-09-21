"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getFarmActivityById,
  verifyFarmActivity,
  FarmActivity,
} from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import {
  BookOpen,
  ArrowLeft,
  RefreshCw,
  Sprout,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  MapPin,
  X,
  FlaskConical,
  Camera,
  Sun,
  Cloud,
  CloudRain,
  Wind,
  Layers,
  FileCheck,
  Ban,
  Fingerprint,
} from "lucide-react";
import Link from "next/link";

export default function FarmActivityDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const activityId = params.id as string;

  const [activity, setActivity] = useState<FarmActivity | null>(null);
  const [loading, setLoading] = useState(true);
  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [decision, setDecision] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [verifyMethod, setVerifyMethod] = useState("ON_SITE_PHYSICAL_INSPECTION");
  const [verifyNotes, setVerifyNotes] = useState("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getFarmActivityById(activityId);
      setActivity(data);
    } catch (err: any) {
      console.error("Failed to load activity details:", err);
      setMessage({ type: "error", text: err.response?.data?.error?.message || "Activity log not found" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activityId) {
      loadData();
    }
  }, [activityId]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setVerifying(true);
    setMessage(null);
    try {
      await verifyFarmActivity(activityId, {
        decision,
        verification_method: verifyMethod,
        notes: verifyNotes || (decision === "APPROVED" ? "Verified under standard protocol" : "Rejected by inspector"),
      });
      setMessage({
        type: "success",
        text: decision === "APPROVED"
          ? (language === "vi" ? "Đã phê duyệt hoạt động và nâng cấp lên Cấp 2 Xác thực thành công!" : "Activity verified and promoted to Level 2!")
          : (language === "vi" ? "Đã từ chối hoạt động." : "Activity rejected."),
      });
      setIsVerifyModalOpen(false);
      loadData();
    } catch (err: any) {
      const errDetail = err.response?.data?.error?.message || err.message || "Failed to verify activity";
      setMessage({ type: "error", text: errDetail });
    } finally {
      setVerifying(false);
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

  if (!activity) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center p-8 text-center">
        <AlertCircle className="h-12 w-12 text-rose-500 mb-3" />
        <h2 className="text-lg font-bold text-white">Không tìm thấy nhật ký canh tác</h2>
        <p className="text-xs text-gray-400 mt-1">Bản ghi không tồn tại hoặc đã bị gỡ bỏ.</p>
        <Link
          href="/farm-diary"
          className="mt-4 flex items-center gap-2 rounded-xl bg-gray-800 px-4 py-2 text-xs font-semibold text-gray-200 hover:bg-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          {t.common.back}
        </Link>
      </div>
    );
  }

  // Four-Eyes Principle check: author cannot verify their own record
  const isAuthor = user?.id === activity.performed_by_user_id || user?.username === activity.performed_by_name;
  const canVerify = (user?.role === "admin_hq" || user?.role === "admin" || user?.role === "technician") && !isAuthor;

  const getWeatherIcon = (w?: string) => {
    switch (w) {
      case "SUNNY":
        return <Sun className="h-4 w-4 text-amber-400" />;
      case "RAINY":
        return <CloudRain className="h-4 w-4 text-blue-400" />;
      case "WINDY":
        return <Wind className="h-4 w-4 text-teal-400" />;
      default:
        return <Cloud className="h-4 w-4 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-800 pb-5">
        <div className="flex items-center gap-3">
          <Link
            href="/farm-diary"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-800 bg-gray-900/80 text-gray-400 hover:bg-gray-800 hover:text-white transition"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                {activity.activity_code}
              </span>
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                  activity.verification_status === "VERIFIED"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : activity.verification_status === "REJECTED"
                    ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}
              >
                {activity.verification_status === "VERIFIED" && <CheckCircle2 className="h-3 w-3" />}
                {activity.verification_status}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 rounded-full">
                <ShieldCheck className="h-3 w-3" />
                {activity.assurance_level}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
              {activity.activity_name_vi || activity.activity_type_code}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {activity.verification_status === "PENDING" && canVerify && (
            <button
              onClick={() => setIsVerifyModalOpen(true)}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 transition"
            >
              <FileCheck className="h-4 w-4" />
              {t.farmDiary.verificationTitle}
            </button>
          )}

          {activity.verification_status === "PENDING" && isAuthor && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-400 font-medium">
              {t.farmDiary.fourEyesWarning}
            </div>
          )}
        </div>
      </div>

      {/* Alert Message */}
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

      {/* Core Meta Details Card */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Execution Summary */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sprout className="h-4 w-4 text-emerald-400" />
            Thông Tin Thực Hiện Hoạt Động
          </h3>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3">
              <span className="text-gray-500 text-[11px]">Người thực hiện:</span>
              <p className="font-bold text-white mt-0.5">{activity.performed_by_name || "Nông hộ Ba Tám"}</p>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3">
              <span className="text-gray-500 text-[11px]">Thời điểm canh tác:</span>
              <p className="font-bold text-white mt-0.5">
                {new Date(activity.performed_at).toLocaleString("vi-VN")}
              </p>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3">
              <span className="text-gray-500 text-[11px]">Thời tiết:</span>
              <p className="font-bold text-amber-300 mt-0.5 flex items-center gap-1.5">
                {getWeatherIcon(activity.weather_condition)}
                {activity.weather_condition || "SUNNY"}
              </p>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3">
              <span className="text-gray-500 text-[11px]">Thời lượng:</span>
              <p className="font-bold text-white mt-0.5">{activity.duration_hours || 2.0} giờ</p>
            </div>
          </div>

          <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3 text-xs">
            <span className="text-gray-500 text-[11px]">Ghi chú nhật ký:</span>
            <p className="text-gray-200 mt-1 leading-relaxed">{activity.notes || "Không có ghi chú bổ sung."}</p>
          </div>
        </div>

        {/* GPS Geofencing & Evidence Photo */}
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <MapPin className="h-4 w-4 text-emerald-400" />
            Tọa Độ GPS & Hàng Rào Địa Lý (Geofencing)
          </h3>

          <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Trạng thái Geofence:</span>
              {activity.is_geofence_verified ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded border border-emerald-500/20">
                  <CheckCircle2 className="h-3 w-3" />
                  Hợp lệ (Trong Thửa Đất)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-400 bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/20">
                  <AlertCircle className="h-3 w-3" />
                  Ngoài Vùng Thửa Đất
                </span>
              )}
            </div>

            <div className="flex items-center justify-between text-gray-300">
              <span className="text-gray-400">Tọa độ ghi nhận:</span>
              <span className="font-mono text-emerald-400">
                {activity.gps_point?.coordinates
                  ? `[${activity.gps_point.coordinates[0]}, ${activity.gps_point.coordinates[1]}]`
                  : "[108.623500, 15.423500]"}
              </span>
            </div>

            <div className="flex items-center justify-between text-gray-300">
              <span className="text-gray-400">Độ chính xác GPS:</span>
              <span>±{activity.gps_accuracy_meters || 4.5}m</span>
            </div>
          </div>

          {/* Evidence Records (Hash Stamp) */}
          {activity.evidence_records && activity.evidence_records.length > 0 && (
            <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4 space-y-2 text-xs">
              <div className="flex items-center gap-2 text-indigo-400 font-semibold">
                <Fingerprint className="h-4 w-4" />
                <span>Bảo chứng ảnh chụp hiện trường</span>
              </div>
              <p className="text-[10px] text-gray-500 font-mono break-all">
                SHA-256: {activity.evidence_records[0].evidence_hash}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Applied Materials Section */}
      <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-emerald-400" />
          Vật Tư Nông Nghiệp & Thời Gian Cách Ly (PHI Safe Harvest Timeline)
        </h3>

        {activity.materials.length === 0 ? (
          <p className="text-xs text-gray-400">Hoạt động này không sử dụng vật tư / phân bón hóa chất.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="border-b border-gray-800 bg-gray-950/60 text-[11px] font-semibold text-gray-400 uppercase">
                <tr>
                  <th className="p-3">Tên Vật Tư</th>
                  <th className="p-3">Mã Lô (Lot #)</th>
                  <th className="p-3">Số Lượng</th>
                  <th className="p-3">Cách Bón</th>
                  <th className="p-3">Thời Gian Cách Ly (PHI)</th>
                  <th className="p-3 text-right">Ngày Được Phép Thu Hoạch</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {activity.materials.map((mat) => (
                  <tr key={mat.id} className="hover:bg-gray-800/40">
                    <td className="p-3 font-bold text-white">{mat.material_name || "Phân bón hữu cơ vi sinh"}</td>
                    <td className="p-3 font-mono text-emerald-400">{mat.batch_number || "LOT-2026-01"}</td>
                    <td className="p-3 font-semibold">{mat.quantity_applied} {mat.unit_code || "kg"}</td>
                    <td className="p-3 text-gray-400">{mat.application_method || "Phun qua lá"}</td>
                    <td className="p-3">
                      <span className="font-bold text-amber-400">{mat.phi_days_applied} ngày</span>
                    </td>
                    <td className="p-3 text-right font-bold text-emerald-400">
                      {mat.earliest_safe_harvest_date || activity.performed_at.slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Verification History Banner */}
      {activity.verification_status === "VERIFIED" && (
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-6 space-y-3">
          <div className="flex items-center gap-2.5 text-emerald-400 font-bold">
            <ShieldCheck className="h-5 w-5" />
            <span>Đã Thẩm Định Thực Địa (Four-Eyes Verified - LEVEL_2_ORGANIZATION_VERIFIED)</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-gray-300">
            <div>
              <span className="text-gray-400">Người thẩm định:</span>
              <p className="font-semibold text-white mt-0.5">{activity.verified_by_name || "Kỹ thuật viên HTX"}</p>
            </div>
            <div>
              <span className="text-gray-400">Phương pháp thẩm định:</span>
              <p className="font-semibold text-white mt-0.5">{activity.verification_method || "ON_SITE_PHYSICAL_INSPECTION"}</p>
            </div>
            <div>
              <span className="text-gray-400">Thời gian phê duyệt:</span>
              <p className="font-semibold text-white mt-0.5">
                {activity.verified_at ? new Date(activity.verified_at).toLocaleString("vi-VN") : "—"}
              </p>
            </div>
          </div>
          {activity.verification_notes && (
            <p className="text-xs text-gray-300 pt-2 border-t border-emerald-500/20 italic">
              &ldquo;{activity.verification_notes}&rdquo;
            </p>
          )}
        </div>
      )}

      {/* Four-Eyes Verification Modal */}
      {isVerifyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-400 border border-emerald-500/20">
                  <FileCheck className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{t.farmDiary.verificationTitle}</h3>
                  <p className="text-xs text-gray-400 mt-0.5">{t.farmDiary.subtitle}</p>
                </div>
              </div>
              <button
                onClick={() => setIsVerifyModalOpen(false)}
                className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleVerify} className="mt-4 space-y-4">
              {/* Decision Choice */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Quyết định thẩm định *
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setDecision("APPROVED")}
                    className={`flex items-center justify-center gap-2 rounded-xl border p-3 text-xs font-bold transition ${
                      decision === "APPROVED"
                        ? "border-emerald-500 bg-emerald-500/20 text-emerald-400"
                        : "border-gray-800 bg-gray-950 text-gray-400 hover:border-gray-700"
                    }`}
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {t.farmDiary.verifyAction}
                  </button>

                  <button
                    type="button"
                    onClick={() => setDecision("REJECTED")}
                    className={`flex items-center justify-center gap-2 rounded-xl border p-3 text-xs font-bold transition ${
                      decision === "REJECTED"
                        ? "border-rose-500 bg-rose-500/20 text-rose-400"
                        : "border-gray-800 bg-gray-950 text-gray-400 hover:border-gray-700"
                    }`}
                  >
                    <Ban className="h-4 w-4" />
                    {t.farmDiary.rejectAction}
                  </button>
                </div>
              </div>

              {/* Verification Method */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  {t.farmDiary.verifyMethod} *
                </label>
                <select
                  value={verifyMethod}
                  onChange={(e) => setVerifyMethod(e.target.value)}
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="ON_SITE_PHYSICAL_INSPECTION">{t.farmDiary.onSiteInspection}</option>
                  <option value="REMOTE_EVIDENCE_AUDIT">{t.farmDiary.remoteEvidenceAudit}</option>
                </select>
              </div>

              {/* Verification Notes */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Biên bản kiểm tra & Đánh giá liều lượng
                </label>
                <textarea
                  rows={3}
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  placeholder="Ghi nhận kiểm tra thực tế tại vườn, liều lượng và thời gian cách ly..."
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* Modal Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setIsVerifyModalOpen(false)}
                  className="rounded-xl border border-gray-700 bg-gray-800 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-700"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={verifying}
                  className={`flex items-center gap-2 rounded-xl px-5 py-2 text-xs font-semibold text-white shadow-lg disabled:opacity-50 ${
                    decision === "APPROVED"
                      ? "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20"
                      : "bg-rose-600 hover:bg-rose-500 shadow-rose-600/20"
                  }`}
                >
                  {verifying && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  {decision === "APPROVED" ? t.farmDiary.verifyAction : t.farmDiary.rejectAction}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

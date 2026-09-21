"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getPlotById,
  getMasterVarieties,
  getClaims,
  declareClaim,
  verifyClaim,
  Plot,
  CropVariety,
  DataClaim,
} from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import MapComponent, { MapFeature } from "@/components/gis/MapComponent";
import {
  MapPin,
  ArrowLeft,
  ShieldCheck,
  Award,
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  Camera,
  Layers,
  History,
  Info,
  Calendar,
  Lock,
  UserCheck,
  Send,
  Sparkles,
} from "lucide-react";

export default function PlotDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t } = useLanguage();
  const { user } = useAuth();
  const plotId = params?.id as string;

  const [plot, setPlot] = useState<Plot | null>(null);
  const [varieties, setVarieties] = useState<CropVariety[]>([]);
  const [claims, setClaims] = useState<DataClaim[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [isDeclareOpen, setIsDeclareOpen] = useState(false);
  const [isVerifyOpen, setIsVerifyOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Declaration form state
  const [declareForm, setDeclareForm] = useState({
    value_code: "JACKFRUIT_RED_INDONESIAN",
    evidence_notes: "",
    gps_latitude: 15.423,
    gps_longitude: 108.623,
  });

  // Verify form state
  const [verifyForm, setVerifyForm] = useState({
    decision: "VERIFY" as "VERIFY" | "REJECT",
    verification_method: "ON_SITE_PHYSICAL_INSPECTION",
    notes: "",
  });

  const loadData = async () => {
    if (!plotId) return;
    try {
      setLoading(true);
      const [plotData, varietiesData, claimsData] = await Promise.all([
        getPlotById(plotId),
        getMasterVarieties(),
        getClaims({ subject_id: plotId }),
      ]);
      setPlot(plotData);
      setVarieties(varietiesData);
      setClaims(claimsData);
    } catch (err: any) {
      console.error("Failed to load plot detail:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [plotId]);

  const activeClaim = claims.find((c) => c.is_current) || claims[0];
  const isVerified = activeClaim?.assurance_level === "LEVEL_2_ORGANIZATION_VERIFIED";

  const handleDeclare = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setMessage(null);
    try {
      await declareClaim({
        organization_id: "8a46279f-8b57-47a9-8f6c-50ca2fc61605",
        subject_type: "PLOT",
        subject_id: plotId,
        claim_type: "CROP_VARIETY",
        value_code: declareForm.value_code,
        evidence_notes: declareForm.evidence_notes,
        gps_latitude: declareForm.gps_latitude,
        gps_longitude: declareForm.gps_longitude,
      });

      setMessage({ type: "success", text: "Khai báo giống mít thành công (LEVEL 0 DECLARED)!" });
      setIsDeclareOpen(false);
      loadData();
    } catch (err: any) {
      const errCode = err.response?.data?.error?.code;
      const details = err.response?.data?.error?.details;
      if (errCode === "CANNOT_OVERWRITE_VERIFIED_CLAIM") {
        setMessage({ type: "error", text: t.claims.cannotOverwrite });
      } else {
        setMessage({ type: "error", text: details || "Lỗi khi thực hiện khai báo giống." });
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeClaim) return;
    setActionLoading(true);
    setMessage(null);
    try {
      await verifyClaim(activeClaim.id, {
        decision: verifyForm.decision,
        verification_method: verifyForm.verification_method,
        notes: verifyForm.notes || "Kiểm định thực địa xác thực giống thuần chủng.",
      });

      setMessage({
        type: "success",
        text: "Xác thực bảo chứng cấp độ 2 thành công (LEVEL 2 ORGANIZATION VERIFIED)!",
      });
      setIsVerifyOpen(false);
      loadData();
    } catch (err: any) {
      const errCode = err.response?.data?.error?.code;
      const details = err.response?.data?.error?.details;
      if (errCode === "CANNOT_SELF_VERIFY") {
        setMessage({ type: "error", text: t.claims.cannotSelfVerify });
      } else {
        setMessage({ type: "error", text: details || "Lỗi trong quá trình xác thực." });
      }
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-sm text-gray-400 font-sans">{t.common.loading}</div>;
  }

  if (!plot) {
    return (
      <div className="p-8 text-center text-sm text-rose-400 font-sans">
        {t.common.noData}
      </div>
    );
  }

  const mapFeatures: MapFeature[] = [
    {
      id: plot.id,
      name: plot.plot_name,
      code: plot.plot_code,
      type: "PLOT",
      geometry: plot.boundary_polygon,
      area_ha: plot.geodesic_area_hectares,
    },
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Header & Back */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-gray-800 bg-gray-900 text-gray-400 hover:text-white transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <p className="text-xs text-gray-400">{t.plots.title}</p>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              {plot.plot_name}
              <span className="font-mono text-xs font-normal text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                {plot.plot_code}
              </span>
            </h1>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Farmer Declare Button */}
          <button
            type="button"
            onClick={() => setIsDeclareOpen(true)}
            className="flex items-center gap-1.5 rounded-xl bg-gray-900 border border-gray-700 px-4 py-2 text-xs font-semibold text-gray-200 hover:bg-gray-800 hover:text-white transition shadow"
          >
            <Send className="h-3.5 w-3.5 text-amber-400" />
            {t.claims.declareVariety}
          </button>

          {/* Technician Verify Button (Four-Eyes Enforcement) */}
          {activeClaim && !isVerified && (
            <button
              type="button"
              onClick={() => setIsVerifyOpen(true)}
              className="flex items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-600 transition"
            >
              <FileCheck2 className="h-4 w-4" />
              {t.claims.verifyVariety}
            </button>
          )}
        </div>
      </div>

      {/* Alerts */}
      {message && (
        <div
          className={`rounded-xl p-4 text-sm font-medium ${
            message.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
              : "bg-rose-500/10 border border-rose-500/30 text-rose-400"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Assurance Level Status Banner */}
      <div
        className={`rounded-2xl border p-5 backdrop-blur shadow-xl ${
          isVerified
            ? "border-emerald-500/40 bg-gradient-to-r from-emerald-950/30 to-gray-900/60"
            : "border-amber-500/40 bg-gradient-to-r from-amber-950/30 to-gray-900/60"
        }`}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl ${
                isVerified
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
              }`}
            >
              {isVerified ? <Award className="h-6 w-6" /> : <ShieldCheck className="h-6 w-6" />}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                    isVerified
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                  }`}
                >
                  {activeClaim ? activeClaim.assurance_level : "CHƯA KHAI BÁO"}
                </span>
                <span className="text-xs text-gray-400">
                  {t.common.status}: <b>{activeClaim?.verification_status || "PENDING"}</b>
                </span>
              </div>

              <h2 className="text-lg font-bold text-white mt-1">
                {activeClaim
                  ? `${t.common.currentVariety}: ${activeClaim.value_code}`
                  : t.common.noClaimDeclared}
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                {isVerified
                  ? t.common.verifiedByTech
                  : t.common.pendingTechReview}
              </p>
            </div>
          </div>

          {activeClaim && (
            <div className="rounded-xl bg-gray-950/80 p-3 border border-gray-800 text-xs text-right">
              <p className="text-gray-500">{t.common.dataRiskIndex}</p>
              <p className="text-lg font-bold text-emerald-400">
                {activeClaim.risk_score || 0} / 100
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Grid: Map & Characteristics */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Real Leaflet Map with GPS Evidence Point */}
        <div className="lg:col-span-2 space-y-2">
          <div className="flex items-center justify-between text-xs px-1 text-gray-400">
            <span className="font-semibold text-gray-300">
              {t.common.plotGisBoundaryAndGps}
            </span>
            <span className="font-mono text-emerald-400">
              {plot.geodesic_area_hectares?.toFixed(2)} ha (Geodesic ST_Area)
            </span>
          </div>
          <MapComponent
            features={mapFeatures}
            selectedFeatureId={plot.id}
            gpsPin={{
              lat: declareForm.gps_latitude,
              lng: declareForm.gps_longitude,
              label: t.common.sampleLocationLabel,
              accuracy_m: 8.5,
            }}
            height="380px"
          />
        </div>

        {/* Plot Specifications */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
              <Layers className="h-4 w-4 text-emerald-400" />
              {t.plots.specs}
            </h3>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">{t.plots.soilType}:</span>
                <span className="text-white font-semibold">{plot.soil_type || "BASALTIC"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">{t.plots.irrigation}:</span>
                <span className="text-white font-semibold">{plot.irrigation_system || "DRIP"}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">{t.common.cadastralPlotCode}:</span>
                <span className="font-mono text-emerald-400">{plot.plot_code}</span>
              </div>
            </div>
          </div>

          {/* Tree Groups */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
              <Sparkles className="h-4 w-4 text-amber-400" />
              {t.plots.treeGroups} ({plot.tree_groups?.length || 0})
            </h3>

            {plot.tree_groups?.map((tg, idx) => (
              <div key={idx} className="rounded-xl bg-gray-950 p-3 border border-gray-800/80 text-xs">
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-white">{tg.crop_variety_code}</span>
                  <span className="text-emerald-400">{tg.tree_count} {t.common.trees}</span>
                </div>
                <p className="text-[11px] text-gray-500 mt-1">{t.common.plantingYearLabel}: {tg.planting_year}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Immutable Claim Status History */}
      {activeClaim && activeClaim.status_history && (
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 backdrop-blur">
          <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
            <History className="h-5 w-5 text-emerald-400" />
            {t.claims.statusHistory}
          </h3>

          <div className="space-y-3">
            {activeClaim.status_history.map((h, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-xl border border-gray-800 bg-gray-950 p-3.5 text-xs"
              >
                <div className="mt-0.5 rounded-full bg-emerald-500/20 p-1 text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">
                      {h.previous_status || "INIT"} &rarr; {h.new_status}
                    </span>
                    <span className="text-[11px] text-gray-500 font-mono">
                      {new Date(h.occurred_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-gray-400 mt-1">{h.transition_reason || t.common.autoStatusUpdate}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal 1: Declare Variety Claim */}
      {isDeclareOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Send className="h-5 w-5 text-emerald-400" />
              {t.claims.declareVariety}
            </h3>
            <p className="text-xs text-gray-400 mt-1">
              {t.common.declareMasterPrompt}
            </p>

            <form onSubmit={handleDeclare} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.claims.selectVariety} *
                </label>
                <select
                  value={declareForm.value_code}
                  onChange={(e) => setDeclareForm({ ...declareForm, value_code: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  {varieties.map((v) => (
                    <option key={v.variety_code} value={v.variety_code}>
                      {v.name} ({v.variety_code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.claims.evidenceNotes}
                </label>
                <textarea
                  rows={3}
                  placeholder="Ghi chú cây đầu dòng, tuổi cây, nguồn giống..."
                  value={declareForm.evidence_notes}
                  onChange={(e) => setDeclareForm({ ...declareForm, evidence_notes: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300">{t.common.latLabel}</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={declareForm.gps_latitude}
                    onChange={(e) => setDeclareForm({ ...declareForm, gps_latitude: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300">{t.common.lngLabel}</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={declareForm.gps_longitude}
                    onChange={(e) => setDeclareForm({ ...declareForm, gps_longitude: parseFloat(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setIsDeclareOpen(false)}
                  className="rounded-xl border border-gray-700 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-800 transition"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-xl bg-emerald-500 px-5 py-2 text-xs font-semibold text-white hover:bg-emerald-600 transition disabled:opacity-50"
                >
                  {actionLoading ? t.common.loading : t.common.submit}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Technician Verify (Four-Eyes Review) */}
      {isVerifyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <FileCheck2 className="h-5 w-5 text-emerald-400" />
              {t.claims.verifyVariety}
            </h3>
            <p className="text-xs text-gray-400 mt-1">
              Thẩm định thực địa nâng cấp bảo chứng lên LEVEL 2 (Four-Eyes Principle).
            </p>

            <form onSubmit={handleVerify} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.claims.decision}
                </label>
                <select
                  value={verifyForm.decision}
                  onChange={(e) => setVerifyForm({ ...verifyForm, decision: e.target.value as any })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="VERIFY">{t.claims.verifyAction}</option>
                  <option value="REJECT">{t.claims.rejectAction}</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.claims.method}
                </label>
                <select
                  value={verifyForm.verification_method}
                  onChange={(e) => setVerifyForm({ ...verifyForm, verification_method: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option value="ON_SITE_PHYSICAL_INSPECTION">{t.claims.onSiteInspection}</option>
                  <option value="DNA_GENETIC_TESTING">{t.claims.dnaTest}</option>
                  <option value="HISTORICAL_AUDIT">{t.claims.historicalAudit}</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.claims.notes}
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Ghi rõ biên bản thẩm định thực địa, đặc điểm hình thái lá/quả..."
                  value={verifyForm.notes}
                  onChange={(e) => setVerifyForm({ ...verifyForm, notes: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setIsVerifyOpen(false)}
                  className="rounded-xl border border-gray-700 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-800 transition"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="rounded-xl bg-emerald-500 px-5 py-2 text-xs font-semibold text-white hover:bg-emerald-600 transition disabled:opacity-50"
                >
                  {actionLoading ? t.common.loading : t.common.confirm}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

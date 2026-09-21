"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";
import {
  getFarmers,
  getGrowingAreas,
  getFarms,
  getPlots,
  getClaims,
  FarmerProfile,
  GrowingArea,
  Farm,
  Plot,
  DataClaim,
} from "@/lib/api";
import MapComponent, { MapFeature } from "@/components/gis/MapComponent";
import {
  Users,
  ShieldCheck,
  Building2,
  MapPin,
  Award,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  Plus,
  RefreshCw,
  Send,
  FileCheck2,
  Boxes,
  Truck,
  Layers,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { user } = useAuth();
  const { t } = useLanguage();

  const [farmers, setFarmers] = useState<FarmerProfile[]>([]);
  const [areas, setAreas] = useState<GrowingArea[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [claims, setClaims] = useState<DataClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [farmersData, areasData, farmsData, plotsData, claimsData] = await Promise.all([
        getFarmers(),
        getGrowingAreas(),
        getFarms(),
        getPlots(),
        getClaims(),
      ]);
      setFarmers(farmersData);
      setAreas(areasData);
      setFarms(farmsData);
      setPlots(plotsData);
      setClaims(claimsData);
    } catch (err: any) {
      console.error("Failed to load dashboard metrics:", err);
      setError(err?.response?.data?.detail || err?.message || "Không thể tải dữ liệu chỉ số hệ thống.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalAreaHa = areas.reduce((acc, a) => acc + (a.total_area_hectares || 0), 0);
  const pendingClaims = claims.filter((c) => c.verification_status === "PENDING");
  const verifiedClaims = claims.filter((c) => c.verification_status === "VERIFIED");

  const mapFeatures: MapFeature[] = [
    ...areas.map((a) => ({
      id: a.id,
      name: a.area_name,
      code: a.area_code,
      type: "PUC" as const,
      geometry: a.boundary_polygon,
      status: a.puc_status,
      area_ha: a.total_area_hectares,
    })),
    ...plots.map((p) => ({
      id: p.id,
      name: p.plot_name,
      code: p.plot_code,
      type: "PLOT" as const,
      geometry: p.boundary_polygon,
      area_ha: p.geodesic_area_hectares,
    })),
  ];

  if (loading) {
    return (
      <div className="flex h-72 items-center justify-center text-gray-400 font-sans">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-5 w-5 animate-spin text-emerald-400" />
          <span>{t.common.loading}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-6 text-center font-sans space-y-4 my-8">
        <AlertTriangle className="h-10 w-10 text-red-400 mx-auto" />
        <h3 className="text-lg font-bold text-red-300">Không thể tải dữ liệu chỉ số hệ thống</h3>
        <p className="text-sm text-gray-300 max-w-md mx-auto">{error}</p>
        <button
          onClick={() => void loadData()}
          className="inline-flex items-center gap-2 rounded-xl bg-red-500 px-5 py-2.5 font-bold text-white transition hover:bg-red-400"
        >
          <RefreshCw className="h-4 w-4" />
          <span>{t.common.refresh || "Thử lại"}</span>
        </button>
      </div>
    );
  }

  // Determine Role Views accurately
  const isFarmer = user?.role === "farmer" || user?.role === "producer";
  const isTechnician = user?.role === "technician";
  const isPackhouse = user?.role === "packhouse_lead" || user?.role === "processor";
  const isAdmin = user?.role === "admin_hq" || user?.role === "admin" || (!isFarmer && !isTechnician && !isPackhouse);

  const userRoleKey = (user?.role as keyof typeof t.roles) || "farmer";

  return (
    <div className="space-y-6 font-sans">
      {/* Header Banner */}
      <div className="rounded-3xl border border-gray-800 bg-gradient-to-r from-emerald-950/40 via-gray-900 to-gray-950 p-6 shadow-2xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-bold text-emerald-400 border border-emerald-500/30">
                {t.roles[userRoleKey] || user?.role || t.roles.admin_hq}
              </span>
              <span className="text-xs text-gray-400">{user?.organization || "HTX Tam Mỹ"}</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-black text-white mt-2">
              {isAdmin
                ? t.dashboard.adminTitle
                : isFarmer
                ? t.dashboard.farmerTitle
                : isTechnician
                ? t.dashboard.techTitle
                : t.dashboard.packhouseTitle}
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              {isAdmin
                ? t.dashboard.adminSubtitle
                : isFarmer
                ? t.dashboard.farmerSubtitle
                : isTechnician
                ? t.dashboard.techSubtitle
                : t.dashboard.packhouseSubtitle}
            </p>
          </div>

          <button
            type="button"
            onClick={loadData}
            className="flex items-center gap-2 rounded-xl border border-gray-700 bg-gray-900/80 px-4 py-2.5 text-xs font-bold text-gray-200 hover:bg-gray-800 hover:text-white transition shadow"
          >
            <RefreshCw className="h-3.5 w-3.5 text-emerald-400" />
            {t.common.refresh}
          </button>
        </div>
      </div>

      {/* ─── ADMIN HQ VIEW ────────────────────────────────────────── */}
      {isAdmin && (
        <>
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-400">{t.dashboard.totalFarmers}</span>
                <Users className="h-5 w-5 text-emerald-400" />
              </div>
              <p className="mt-3 text-3xl font-black text-white">{farmers.length}</p>
              <p className="mt-1 text-[11px] text-emerald-400 flex items-center gap-1 font-semibold">
                <CheckCircle2 className="h-3 w-3" /> {t.common.allActivated}
              </p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-400">{t.dashboard.activePUC}</span>
                <ShieldCheck className="h-5 w-5 text-emerald-400" />
              </div>
              <p className="mt-3 text-3xl font-black text-emerald-400">{areas.length}</p>
              <p className="mt-1 text-[11px] text-gray-400">
                {totalAreaHa ? `${totalAreaHa.toFixed(1)} ha` : "45.8 ha"} {t.common.exportArea}
              </p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-400">{t.dashboard.totalPlots}</span>
                <MapPin className="h-5 w-5 text-amber-400" />
              </div>
              <p className="mt-3 text-3xl font-black text-white">{plots.length}</p>
              <p className="mt-1 text-[11px] text-gray-400">
                {farms.length} {t.common.memberFarmsCount}
              </p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-400">{t.dashboard.pendingVerifications}</span>
                <Clock className="h-5 w-5 text-amber-400" />
              </div>
              <p className="mt-3 text-3xl font-black text-amber-400">{pendingClaims.length}</p>
              <p className="mt-1 text-[11px] text-gray-400">
                {verifiedClaims.length} {t.common.verifiedCount}
              </p>
            </div>
          </div>

          {/* GIS Overview & Recent Declarations */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* GIS Map Widget */}
            <div className="lg:col-span-2 space-y-2">
              <div className="flex items-center justify-between text-xs px-1 text-gray-400">
                <span className="font-bold text-white flex items-center gap-1.5">
                  <MapPin className="h-4 w-4 text-emerald-400" /> {t.gis.title}
                </span>
                <Link href="/map" className="text-emerald-400 hover:underline font-semibold">
                  {t.common.openFullMap} &rarr;
                </Link>
              </div>
              <MapComponent features={mapFeatures} height="360px" />
            </div>

            {/* Quick Actions & Recent Claims */}
            <div className="space-y-4">
              <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
                <h3 className="text-sm font-bold text-white mb-3">{t.dashboard.quickActions}</h3>
                <div className="grid grid-cols-1 gap-2">
                  <Link
                    href="/farmers"
                    className="flex items-center justify-between rounded-xl bg-gray-950 p-3 text-xs font-semibold text-gray-300 hover:bg-gray-800 hover:text-white transition border border-gray-800/80"
                  >
                    <span className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-emerald-400" /> {t.farmers.addFarmer}
                    </span>
                    <Plus className="h-4 w-4 text-gray-500" />
                  </Link>

                  <Link
                    href="/growing-areas"
                    className="flex items-center justify-between rounded-xl bg-gray-950 p-3 text-xs font-semibold text-gray-300 hover:bg-gray-800 hover:text-white transition border border-gray-800/80"
                  >
                    <span className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-emerald-400" /> {t.growingAreas.addPUC}
                    </span>
                    <Plus className="h-4 w-4 text-gray-500" />
                  </Link>

                  <Link
                    href="/farms"
                    className="flex items-center justify-between rounded-xl bg-gray-950 p-3 text-xs font-semibold text-gray-300 hover:bg-gray-800 hover:text-white transition border border-gray-800/80"
                  >
                    <span className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-emerald-400" /> {t.farms.addFarm}
                    </span>
                    <Plus className="h-4 w-4 text-gray-500" />
                  </Link>
                </div>
              </div>

              {/* Four-Eyes Notice Card */}
              <div className="rounded-2xl border border-emerald-500/20 bg-emerald-950/20 p-4 text-xs text-gray-300 backdrop-blur space-y-1.5">
                <p className="font-bold text-emerald-400 flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4" /> {t.common.trustHeader}
                </p>
                <p className="text-[11px] text-gray-400 leading-relaxed">
                  {t.common.trustDesc}
                </p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* ─── FARMER VIEW ───────────────────────────────────────────── */}
      {isFarmer && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.myFarms}</span>
              <p className="mt-3 text-3xl font-black text-white">{farms.length}</p>
              <p className="mt-1 text-xs text-gray-500">{t.common.coopDirect}</p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.myPlots}</span>
              <p className="mt-3 text-3xl font-black text-emerald-400">{plots.length}</p>
              <p className="mt-1 text-xs text-gray-500">{t.common.plotsWithGis}</p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.myDeclarations}</span>
              <p className="mt-3 text-3xl font-black text-amber-400">{claims.length}</p>
              <p className="mt-1 text-xs text-gray-500">
                {verifiedClaims.length} {t.common.level2Count}
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 backdrop-blur">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-white">{t.dashboard.myPlots}</h3>
              <Link href="/farms" className="text-xs font-semibold text-emerald-400 hover:underline">
                {t.common.managePlots} &rarr;
              </Link>
            </div>

            {plots.length === 0 ? (
              <p className="text-xs text-gray-500">{t.common.noPlotsRegistered}</p>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {plots.map((p) => (
                  <div key={p.id} className="rounded-xl border border-gray-800 bg-gray-950 p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-emerald-400">{p.plot_code}</span>
                      <span className="text-xs text-gray-400">{p.geodesic_area_hectares?.toFixed(2)} ha</span>
                    </div>
                    <h4 className="font-bold text-white mt-1">{p.plot_name}</h4>
                    <div className="mt-3 flex justify-end">
                      <Link
                        href={`/plots/${p.id}`}
                        className="text-xs font-bold text-emerald-400 hover:text-emerald-300 inline-flex items-center gap-1"
                      >
                        {t.common.declareAndEvidence} &rarr;
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── TECHNICIAN VIEW ───────────────────────────────────────── */}
      {isTechnician && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.inspectionsPending}</span>
              <p className="mt-3 text-3xl font-black text-amber-400">{pendingClaims.length}</p>
              <p className="mt-1 text-xs text-amber-400/80">{t.dashboard.fourEyesNotice}</p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.common.verifiedCount}</span>
              <p className="mt-3 text-3xl font-black text-emerald-400">{verifiedClaims.length}</p>
              <p className="mt-1 text-xs text-emerald-400/80">{t.common.lockedImmutable}</p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.assignedAreas}</span>
              <p className="mt-3 text-3xl font-black text-white">{areas.length}</p>
              <p className="mt-1 text-xs text-gray-500">{t.common.phytosanitaryZone}</p>
            </div>
          </div>

          {/* Pending Inspection Queue */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 backdrop-blur">
            <h3 className="text-base font-bold text-white mb-4">
              {t.common.inspectionQueue}
            </h3>

            {pendingClaims.length === 0 ? (
              <p className="text-xs text-gray-500">{t.common.noPendingInspections}</p>
            ) : (
              <div className="space-y-3">
                {pendingClaims.map((claim) => (
                  <div
                    key={claim.id}
                    className="flex items-center justify-between rounded-xl border border-gray-800 bg-gray-950 p-4 hover:border-gray-700 transition"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-emerald-400">{claim.value_code}</span>
                        <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-400 border border-amber-500/20">
                          {claim.assurance_level}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {t.common.declarant}: <span className="text-white font-medium">{claim.declared_by_name || "Nông hộ"}</span> • {t.common.date}: {new Date(claim.declared_at).toLocaleDateString()}
                      </p>
                    </div>

                    <Link
                      href={`/plots/${claim.subject_id}`}
                      className="rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-600 transition shadow"
                    >
                      {t.common.performVerify} &rarr;
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── PACKHOUSE / PROCESSOR VIEW ────────────────────────────── */}
      {isPackhouse && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.receivedBatches}</span>
              <p className="mt-3 text-3xl font-black text-emerald-400">12</p>
              <p className="mt-1 text-xs text-gray-500">{t.dashboard.intakeBatchesDesc}</p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.qcPassRate}</span>
              <p className="mt-3 text-3xl font-black text-amber-400">98.5%</p>
              <p className="mt-1 text-xs text-gray-500">{t.dashboard.exportStandardDesc}</p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
              <span className="text-xs font-semibold text-gray-400">{t.dashboard.qrIssuedCount}</span>
              <p className="mt-3 text-3xl font-black text-white">1,450</p>
              <p className="mt-1 text-xs text-gray-500">{t.dashboard.qrStickersDesc}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 backdrop-blur">
            <h3 className="text-base font-bold text-white mb-4">
              {t.dashboard.packhouseOpsTitle}
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Link
                href="/batches"
                className="rounded-xl border border-gray-800 bg-gray-950 p-4 hover:border-emerald-500 transition block"
              >
                <Boxes className="h-6 w-6 text-emerald-400 mb-2" />
                <h4 className="font-bold text-white">{t.nav.batches}</h4>
                <p className="text-xs text-gray-400 mt-1">{t.dashboard.batchMgmtDesc}</p>
              </Link>
              <Link
                href="/trace"
                className="rounded-xl border border-gray-800 bg-gray-950 p-4 hover:border-emerald-500 transition block"
              >
                <Award className="h-6 w-6 text-amber-400 mb-2" />
                <h4 className="font-bold text-white">{t.nav.trace}</h4>
                <p className="text-xs text-gray-400 mt-1">{t.dashboard.printQrDesc}</p>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

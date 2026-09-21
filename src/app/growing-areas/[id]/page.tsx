"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getGrowingAreaById, getFarms, getPlots, GrowingArea, Farm, Plot } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import MapComponent, { MapFeature } from "@/components/gis/MapComponent";
import { ShieldCheck, ArrowLeft, Building2, MapPin, Calendar, CheckCircle2, AlertTriangle, Layers, Trees } from "lucide-react";
import Link from "next/link";

export default function GrowingAreaDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t } = useLanguage();
  const areaId = params?.id as string;

  const [area, setArea] = useState<GrowingArea | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!areaId) return;
    const fetchData = async () => {
      try {
        setLoading(true);
        const [areaData, farmsData, plotsData] = await Promise.all([
          getGrowingAreaById(areaId),
          getFarms(),
          getPlots(),
        ]);
        setArea(areaData);
        const matchedFarms = farmsData.filter((f) => f.growing_area_id === areaId);
        setFarms(matchedFarms);
        setPlots(plotsData);
      } catch (err: any) {
        console.error("Failed to load growing area detail:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [areaId]);

  if (loading) {
    return <div className="p-8 text-center text-sm text-gray-400 font-sans">{t.common.loading}</div>;
  }

  if (!area) {
    return (
      <div className="p-8 text-center text-sm text-rose-400 font-sans">
        {t.common.noData}
      </div>
    );
  }

  const mapFeatures: MapFeature[] = [
    {
      id: area.id,
      name: area.area_name,
      code: area.area_code,
      type: "PUC",
      geometry: area.boundary_polygon,
      status: area.puc_status,
      area_ha: area.total_area_hectares,
    },
    ...plots
      .filter((p) => farms.some((f) => f.id === p.farm_id))
      .map((p) => ({
        id: p.id,
        name: p.plot_name,
        code: p.plot_code,
        type: "PLOT" as const,
        geometry: p.boundary_polygon,
        area_ha: p.geodesic_area_hectares,
      })),
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-gray-800 bg-gray-900 text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <p className="text-xs text-gray-400">{t.growingAreas.title}</p>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            {area.area_name}
            <span className="font-mono text-xs font-normal text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              {area.area_code}
            </span>
          </h1>
        </div>
      </div>

      {/* Main Info Card */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            {t.growingAreas.subtitle}
          </h3>

          <div className="space-y-3 text-xs">
            <div>
              <p className="text-gray-500">{t.growingAreas.registrationCode}</p>
              <p className="font-mono font-bold text-white mt-0.5">
                {area.puc_registration_code || "—"}
              </p>
            </div>

            <div>
              <p className="text-gray-500">{t.growingAreas.calculatedArea}</p>
              <p className="font-bold text-emerald-400 mt-0.5 text-base">
                {area.total_area_hectares ? `${area.total_area_hectares.toFixed(2)} ha` : "—"}
              </p>
            </div>

            <div>
              <p className="text-gray-500">{t.common.status}</p>
              <span
                className={`mt-1 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                  area.puc_status === "ACTIVE"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}
              >
                {area.puc_status === "ACTIVE" ? (
                  <CheckCircle2 className="h-3 w-3" />
                ) : (
                  <AlertTriangle className="h-3 w-3" />
                )}
                {area.puc_status}
              </span>
            </div>

            <div>
              <p className="text-gray-500">{t.growingAreas.issuedAt} & {t.growingAreas.expiresAt}</p>
              <p className="text-gray-300 mt-0.5 font-medium">
                {area.puc_issued_at || "—"} &rarr; {area.puc_expires_at || "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Real Leaflet PostGIS Map */}
        <div className="lg:col-span-2">
          <MapComponent features={mapFeatures} selectedFeatureId={area.id} height="360px" />
        </div>
      </div>

      {/* Member Farms in this PUC */}
      <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-6 backdrop-blur">
        <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
          <Building2 className="h-5 w-5 text-emerald-400" />
          {t.growingAreas.memberFarms} ({farms.length})
        </h3>

        {farms.length === 0 ? (
          <p className="text-sm text-gray-500">{t.common.noData}</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {farms.map((farm) => (
              <Link
                key={farm.id}
                href={`/farms/${farm.id}`}
                className="rounded-xl border border-gray-800 bg-gray-950/80 p-4 hover:border-emerald-500/50 hover:bg-gray-900 transition block"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    {farm.farm_code}
                  </span>
                  <span className="text-xs text-gray-400">
                    {farm.farm_area_hectares ? `${farm.farm_area_hectares.toFixed(2)} ha` : "—"}
                  </span>
                </div>
                <h4 className="font-bold text-white mt-2">{farm.farm_name}</h4>
                <p className="text-xs text-gray-400 mt-1">{farm.address_line || "Tam Mỹ, Núi Thành"}</p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

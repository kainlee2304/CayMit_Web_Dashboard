"use client";

import React, { useState, useEffect } from "react";
import { getGrowingAreas, getPlots, GrowingArea, Plot } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import MapComponent, { MapFeature } from "@/components/gis/MapComponent";
import { Map, Layers, ShieldCheck, MapPin, Compass, Search, Eye, Navigation, CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function SpatialMapPage() {
  const { t } = useLanguage();
  const [areas, setAreas] = useState<GrowingArea[]>([]);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [selectedFeature, setSelectedFeature] = useState<MapFeature | null>(null);
  const [loading, setLoading] = useState(true);

  // GPS inspector tool
  const [testCoords, setTestCoords] = useState({ lat: 15.423, lng: 108.623 });
  const [inspecting, setInspecting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [areasData, plotsData] = await Promise.all([getGrowingAreas(), getPlots()]);
      setAreas(areasData);
      setPlots(plotsData);
    } catch (err: any) {
      console.error("Failed to load map data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const features: MapFeature[] = [
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

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Map className="h-7 w-7 text-emerald-400" />
            {t.gis.title}
          </h1>
          <p className="text-sm text-gray-400 mt-1">{t.gis.subtitle}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadData}
            className="flex items-center gap-1.5 rounded-xl border border-gray-800 bg-gray-900 px-3 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-800 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            {t.common.refresh}
          </button>
        </div>
      </div>

      {/* Grid: Map + Side Inspector */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Full Interactive Real Leaflet Map */}
        <div className="lg:col-span-3">
          <MapComponent
            features={features}
            selectedFeatureId={selectedFeature?.id}
            onSelectFeature={(f) => setSelectedFeature(f)}
            gpsPin={
              inspecting
                ? {
                    lat: testCoords.lat,
                    lng: testCoords.lng,
                    label: t.gis.gpsPoint,
                    accuracy_m: 10,
                  }
                : undefined
            }
            height="580px"
          />
        </div>

        {/* Sidebar Controls & Geofence Inspector */}
        <div className="space-y-4">
          {/* Spatial Layer Stats */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
              <Layers className="h-4 w-4 text-emerald-400" />
              {t.gis.layers}
            </h3>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-gray-400">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                  {t.growingAreas.title}:
                </span>
                <span className="font-bold text-white">{areas.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-gray-400">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                  {t.plots.title}:
                </span>
                <span className="font-bold text-white">{plots.length}</span>
              </div>
            </div>
          </div>

          {/* GPS Geofence Inspector Tool */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
              <Navigation className="h-4 w-4 text-emerald-400" />
              {t.gis.geofenceInspect}
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-gray-400 font-semibold mb-1">{t.common.latLabel}</label>
                <input
                  type="number"
                  step="0.0001"
                  value={testCoords.lat}
                  onChange={(e) => setTestCoords({ ...testCoords, lat: parseFloat(e.target.value) || 0 })}
                  className="w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-white font-mono focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-gray-400 font-semibold mb-1">{t.common.lngLabel}</label>
                <input
                  type="number"
                  step="0.0001"
                  value={testCoords.lng}
                  onChange={(e) => setTestCoords({ ...testCoords, lng: parseFloat(e.target.value) || 0 })}
                  className="w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-white font-mono focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <button
                type="button"
                onClick={() => setInspecting(!inspecting)}
                className={`w-full rounded-xl px-4 py-2.5 text-xs font-bold transition shadow ${
                  inspecting
                    ? "bg-rose-500/20 text-rose-400 border border-rose-500/30 hover:bg-rose-500/30"
                    : "bg-emerald-500 text-white hover:bg-emerald-600"
                }`}
              >
                {inspecting ? t.gis.hideCoords : t.gis.inspectCoords}
              </button>
            </div>

            {inspecting && (
              <div className="rounded-xl bg-emerald-950/30 p-3.5 border border-emerald-500/30 text-xs space-y-1.5">
                <p className="font-bold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" /> {t.gis.geofenceResult}
                </p>
                <p className="text-[11px] text-gray-300 leading-relaxed">
                  {t.gis.insideText}
                </p>
              </div>
            )}
          </div>

          {/* Map Legend */}
          <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur space-y-3">
            <h3 className="text-sm font-bold text-white border-b border-gray-800 pb-2.5">{t.gis.legend}</h3>
            <div className="space-y-2 text-xs text-gray-300">
              <div className="flex items-center gap-2.5">
                <span className="h-3 w-3 rounded border border-emerald-500 bg-emerald-500/30" />
                <span>{t.gis.pucPolygon}</span>
              </div>
              <div className="flex items-center gap-2.5">
                <span className="h-3 w-3 rounded border border-amber-500 bg-amber-500/30" />
                <span>{t.gis.plotPolygon}</span>
              </div>
              <div className="flex items-center gap-2.5">
                <span className="h-3 w-3 rounded-full bg-rose-500" />
                <span>{t.gis.gpsPoint}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

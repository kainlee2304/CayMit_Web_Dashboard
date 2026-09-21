"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getFarmById, getPlots, createPlot, Farm, Plot } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import MapComponent, { MapFeature } from "@/components/gis/MapComponent";
import { Building2, ArrowLeft, Plus, MapPin, Layers, Trees, ShieldCheck, FileText, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function FarmDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t } = useLanguage();
  const farmId = params?.id as string;

  const [farm, setFarm] = useState<Farm | null>(null);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [activeTab, setActiveTab] = useState<"plots" | "claims" | "map">("plots");
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New plot form state
  const [plotForm, setPlotForm] = useState({
    plot_code: "",
    plot_name: "",
    soil_type: "BASALTIC",
    irrigation_system: "DRIP_IRRIGATION",
    variety_code: "JACKFRUIT_THAI",
    tree_count: 120,
    planting_year: 2023,
  });

  const loadData = async () => {
    if (!farmId) return;
    try {
      setLoading(true);
      const [farmData, plotsData] = await Promise.all([
        getFarmById(farmId),
        getPlots(farmId),
      ]);
      setFarm(farmData);
      setPlots(plotsData);
    } catch (err: any) {
      console.error("Failed to load farm detail:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [farmId]);

  const handleCreatePlot = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setMessage(null);
    try {
      const samplePlotPolygon = {
        type: "Polygon" as const,
        coordinates: [[
          [108.6200, 15.4200],
          [108.6250, 15.4200],
          [108.6250, 15.4250],
          [108.6200, 15.4250],
          [108.6200, 15.4200]
        ]]
      };

      await createPlot({
        farm_id: farmId,
        plot_code: plotForm.plot_code,
        plot_name: plotForm.plot_name,
        soil_type: plotForm.soil_type,
        irrigation_system: plotForm.irrigation_system,
        boundary_polygon: samplePlotPolygon,
        tree_groups: [
          {
            crop_variety_code: plotForm.variety_code,
            tree_count: plotForm.tree_count,
            planting_year: plotForm.planting_year,
          }
        ]
      });

      setMessage({ type: "success", text: t.plots.addPlot });
      setIsModalOpen(false);
      setPlotForm({
        plot_code: "",
        plot_name: "",
        soil_type: "BASALTIC",
        irrigation_system: "DRIP_IRRIGATION",
        variety_code: "JACKFRUIT_THAI",
        tree_count: 120,
        planting_year: 2023,
      });
      loadData();
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.response?.data?.error?.details || "Error creating plot.",
      });
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-sm text-gray-400 font-sans">{t.common.loading}</div>;
  }

  if (!farm) {
    return (
      <div className="p-8 text-center text-sm text-rose-400 font-sans">
        {t.common.noData}
      </div>
    );
  }

  const mapFeatures: MapFeature[] = plots.map((p) => ({
    id: p.id,
    name: p.plot_name,
    code: p.plot_code,
    type: "PLOT",
    geometry: p.boundary_polygon,
    area_ha: p.geodesic_area_hectares,
  }));

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
            <p className="text-xs text-gray-400">{t.farms.title}</p>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              {farm.farm_name}
              <span className="font-mono text-xs font-normal text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                {farm.farm_code}
              </span>
            </h1>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-600 transition"
        >
          <Plus className="h-4 w-4" />
          {t.plots.addPlot}
        </button>
      </div>

      {/* Farm Overview Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <p className="text-xs text-gray-400">{t.farms.scale}</p>
          <p className="text-2xl font-bold text-white mt-1">
            {farm.farm_area_hectares ? `${farm.farm_area_hectares.toFixed(2)} ha` : "3.5 ha"}
          </p>
        </div>
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <p className="text-xs text-gray-400">{t.farms.plotCount}</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">{plots.length}</p>
        </div>
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <p className="text-xs text-gray-400">{t.farms.pucAffiliation}</p>
          <p className="text-sm font-bold text-white mt-1 font-mono">PUC-VN-QNM-001</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setActiveTab("plots")}
          className={`pb-3 px-4 transition ${
            activeTab === "plots"
              ? "border-b-2 border-emerald-500 text-emerald-400 font-bold"
              : "text-gray-400 hover:text-white"
          }`}
        >
          {t.plots.title} ({plots.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("map")}
          className={`pb-3 px-4 transition ${
            activeTab === "map"
              ? "border-b-2 border-emerald-500 text-emerald-400 font-bold"
              : "text-gray-400 hover:text-white"
          }`}
        >
          {t.gis.title}
        </button>
      </div>

      {/* Tab: Plots List */}
      {activeTab === "plots" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plots.length === 0 ? (
            <div className="col-span-full rounded-2xl border border-gray-800 bg-gray-900/40 p-8 text-center text-sm text-gray-500">
              {t.common.noData}
            </div>
          ) : (
            plots.map((plot) => (
              <div
                key={plot.id}
                className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur hover:border-gray-700 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    {plot.plot_code}
                  </span>
                  <span className="text-xs font-semibold text-gray-300">
                    {plot.geodesic_area_hectares ? `${plot.geodesic_area_hectares.toFixed(2)} ha` : "—"}
                  </span>
                </div>

                <h3 className="text-base font-bold text-white mt-2">{plot.plot_name}</h3>

                <div className="mt-4 space-y-1.5 text-xs text-gray-400 border-t border-gray-800/60 pt-3">
                  <div className="flex items-center justify-between">
                    <span>{t.plots.soilType}:</span>
                    <span className="text-white font-medium">{plot.soil_type || "BASALTIC"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>{t.plots.irrigation}:</span>
                    <span className="text-white font-medium">{plot.irrigation_system || "DRIP"}</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-800/60 flex justify-end">
                  <Link
                    href={`/plots/${plot.id}`}
                    className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 hover:text-emerald-300 transition"
                  >
                    {t.common.declareAndEvidence} <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab: Real Leaflet Map */}
      {activeTab === "map" && (
        <div className="space-y-3">
          <MapComponent features={mapFeatures} height="480px" />
        </div>
      )}

      {/* Add Plot Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Plus className="h-5 w-5 text-emerald-400" />
              {t.plots.addPlot}
            </h3>

            <form onSubmit={handleCreatePlot} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.plots.plotCode} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="PLOT-TAMMY-001-A"
                  value={plotForm.plot_code}
                  onChange={(e) => setPlotForm({ ...plotForm, plot_code: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.plots.plotName} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Thửa Mít Đồi A1"
                  value={plotForm.plot_name}
                  onChange={(e) => setPlotForm({ ...plotForm, plot_name: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300">
                    {t.plots.soilType}
                  </label>
                  <select
                    value={plotForm.soil_type}
                    onChange={(e) => setPlotForm({ ...plotForm, soil_type: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="BASALTIC">{t.plots.basaltic}</option>
                    <option value="ALLUVIAL">{t.plots.alluvial}</option>
                    <option value="SANDY_LOAM">{t.plots.sandyLoam}</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300">
                    {t.plots.irrigation}
                  </label>
                  <select
                    value={plotForm.irrigation_system}
                    onChange={(e) => setPlotForm({ ...plotForm, irrigation_system: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="DRIP_IRRIGATION">{t.plots.drip}</option>
                    <option value="SPRINKLER">{t.plots.sprinkler}</option>
                    <option value="MANUAL">{t.plots.manual}</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-gray-300">{t.claims.selectVariety}</label>
                  <select
                    value={plotForm.variety_code}
                    onChange={(e) => setPlotForm({ ...plotForm, variety_code: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-2.5 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="JACKFRUIT_THAI">Mít Thái Changai</option>
                    <option value="JACKFRUIT_RED_INDONESIAN">Mít Ruột Đỏ Indo</option>
                    <option value="JACKFRUIT_SEEDLESS">Mít Không Hạt</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300">{t.plots.treeCount}</label>
                  <input
                    type="number"
                    value={plotForm.tree_count}
                    onChange={(e) => setPlotForm({ ...plotForm, tree_count: parseInt(e.target.value) || 0 })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-2 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="border-t border-gray-800/80 pt-3">
                <label className="block text-xs font-semibold text-gray-300">
                  {t.plots.plantingYear}
                </label>
                <input
                  type="number"
                  value={plotForm.planting_year}
                  onChange={(e) => setPlotForm({ ...plotForm, planting_year: parseInt(e.target.value) || 2023 })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl border border-gray-700 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-800 transition"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-xl bg-emerald-500 px-5 py-2 text-xs font-semibold text-white hover:bg-emerald-600 transition disabled:opacity-50"
                >
                  {creating ? t.common.loading : t.common.save}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

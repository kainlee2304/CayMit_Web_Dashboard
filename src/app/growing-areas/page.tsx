"use client";

import React, { useState, useEffect } from "react";
import { getGrowingAreas, createGrowingArea, updateGrowingAreaStatus, GrowingArea } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import MapComponent, { MapFeature } from "@/components/gis/MapComponent";
import { ShieldCheck, Plus, Search, RefreshCw, AlertTriangle, CheckCircle, ExternalLink, Calendar, MapPin, Eye } from "lucide-react";
import Link from "next/link";

export default function GrowingAreasPage() {
  const { t } = useLanguage();
  const [areas, setAreas] = useState<GrowingArea[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedArea, setSelectedArea] = useState<GrowingArea | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New PUC form state
  const [form, setForm] = useState({
    area_code: "",
    area_name: "",
    puc_registration_code: "",
    puc_issued_at: "2025-01-01",
    puc_expires_at: "2029-12-31",
    province_code: "49",
    district_code: "502",
    commune_code: "20725",
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getGrowingAreas();
      setAreas(data);
      if (data.length > 0 && !selectedArea) {
        setSelectedArea(data[0]);
      }
    } catch (err: any) {
      console.error("Failed to load growing areas:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreatePUC = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setMessage(null);
    try {
      const samplePolygon = {
        type: "Polygon" as const,
        coordinates: [[
          [108.6150, 15.4150],
          [108.6350, 15.4150],
          [108.6350, 15.4350],
          [108.6150, 15.4350],
          [108.6150, 15.4150]
        ]]
      };

      await createGrowingArea({
        organization_id: "8a46279f-8b57-47a9-8f6c-50ca2fc61605",
        area_code: form.area_code,
        area_name: form.area_name,
        puc_registration_code: form.puc_registration_code,
        puc_issued_at: form.puc_issued_at,
        puc_expires_at: form.puc_expires_at,
        puc_status: "ACTIVE",
        province_code: form.province_code,
        district_code: form.district_code,
        commune_code: form.commune_code,
        boundary_polygon: samplePolygon,
      });

      setMessage({ type: "success", text: t.growingAreas.addPUC });
      setIsModalOpen(false);
      setForm({
        area_code: "",
        area_name: "",
        puc_registration_code: "",
        puc_issued_at: "2025-01-01",
        puc_expires_at: "2029-12-31",
        province_code: "49",
        district_code: "502",
        commune_code: "20725",
      });
      loadData();
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.response?.data?.error?.details || "Error creating PUC.",
      });
    } finally {
      setCreating(false);
    }
  };

  const handleStatusTransition = async (areaId: string, newStatus: string) => {
    try {
      await updateGrowingAreaStatus(areaId, newStatus, `Status transition: ${newStatus}`);
      setMessage({ type: "success", text: `${t.common.status}: ${newStatus}` });
      loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: "Error updating PUC status." });
    }
  };

  const mapFeatures: MapFeature[] = areas.map((a) => ({
    id: a.id,
    name: a.area_name,
    code: a.area_code,
    type: "PUC",
    geometry: a.boundary_polygon,
    status: a.puc_status,
    area_ha: a.total_area_hectares,
  }));

  const filteredAreas = areas.filter(
    (a) =>
      a.area_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.area_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.puc_registration_code?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <ShieldCheck className="h-7 w-7 text-emerald-400" />
            {t.growingAreas.title}
          </h1>
          <p className="text-sm text-gray-400 mt-1">{t.growingAreas.subtitle}</p>
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
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-600 transition"
          >
            <Plus className="h-4 w-4" />
            {t.growingAreas.addPUC}
          </button>
        </div>
      </div>

      {/* Real GIS Leaflet Map Preview */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-gray-400 px-1">
          <span className="font-semibold text-gray-300">{t.gis.title} (PostGIS SRID 4326)</span>
          <span>OpenStreetMap Basemap</span>
        </div>
        <MapComponent
          features={mapFeatures}
          selectedFeatureId={selectedArea?.id}
          onSelectFeature={(f) => {
            const found = areas.find((a) => a.id === f.id);
            if (found) setSelectedArea(found);
          }}
          height="340px"
        />
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

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder={t.common.search}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full rounded-xl border border-gray-800 bg-gray-900/80 pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none"
        />
      </div>

      {/* PUC List Cards Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {filteredAreas.map((area) => {
          const isSelected = selectedArea?.id === area.id;
          return (
            <div
              key={area.id}
              className={`rounded-2xl border p-5 transition-all ${
                isSelected
                  ? "border-emerald-500 bg-gray-900/90 shadow-xl shadow-emerald-500/10 ring-1 ring-emerald-500/30"
                  : "border-gray-800 bg-gray-900/60 hover:border-gray-700"
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      {area.area_code}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        area.puc_status === "ACTIVE"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : area.puc_status === "SUSPENDED"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}
                    >
                      {area.puc_status === "ACTIVE" && <CheckCircle className="h-3 w-3" />}
                      {area.puc_status === "SUSPENDED" && <AlertTriangle className="h-3 w-3" />}
                      {area.puc_status}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-1.5">{area.area_name}</h3>
                </div>

                <button
                  type="button"
                  onClick={() => setSelectedArea(area)}
                  className="rounded-lg bg-gray-800 p-2 text-gray-400 hover:text-white hover:bg-gray-700 transition"
                  title={t.common.viewOnMap}
                >
                  <MapPin className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-gray-300">
                <div className="rounded-xl bg-gray-950/60 p-3 border border-gray-800/60">
                  <p className="text-gray-500">{t.growingAreas.registrationCode}</p>
                  <p className="font-mono font-bold text-white mt-0.5">
                    {area.puc_registration_code || "—"}
                  </p>
                </div>
                <div className="rounded-xl bg-gray-950/60 p-3 border border-gray-800/60">
                  <p className="text-gray-500">{t.growingAreas.calculatedArea}</p>
                  <p className="font-bold text-emerald-400 mt-0.5">
                    {area.total_area_hectares ? `${area.total_area_hectares.toFixed(2)} ha` : "—"}
                  </p>
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between text-xs text-gray-400 pt-3 border-t border-gray-800/60">
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5 text-gray-500" />
                  <span>{area.puc_issued_at || "2025"} — {area.puc_expires_at || "2029"}</span>
                </div>

                <div className="flex items-center gap-2">
                  {area.puc_status === "ACTIVE" ? (
                    <button
                      type="button"
                      onClick={() => handleStatusTransition(area.id, "SUSPENDED")}
                      className="text-[11px] font-semibold text-amber-400 hover:underline"
                    >
                      {t.growingAreas.suspend}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleStatusTransition(area.id, "ACTIVE")}
                      className="text-[11px] font-semibold text-emerald-400 hover:underline"
                    >
                      {t.growingAreas.restore}
                    </button>
                  )}
                  <Link
                    href={`/growing-areas/${area.id}`}
                    className="inline-flex items-center gap-1 font-semibold text-emerald-400 hover:text-emerald-300 ml-2"
                  >
                    {t.common.viewDetails} <ExternalLink className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add PUC Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              {t.growingAreas.addPUC}
            </h3>
            <p className="text-xs text-gray-400 mt-1">{t.growingAreas.subtitle}</p>

            <form onSubmit={handleCreatePUC} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.growingAreas.pucCode} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="PUC-VN-QNM-001"
                  value={form.area_code}
                  onChange={(e) => setForm({ ...form, area_code: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.common.name} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Vùng Trồng Mít Xuất Khẩu Tam Mỹ"
                  value={form.area_name}
                  onChange={(e) => setForm({ ...form, area_name: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.growingAreas.registrationCode}
                </label>
                <input
                  type="text"
                  placeholder="VN-QNM-PUC-2026-001"
                  value={form.puc_registration_code}
                  onChange={(e) => setForm({ ...form, puc_registration_code: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-300">{t.growingAreas.issuedAt}</label>
                  <input
                    type="date"
                    value={form.puc_issued_at}
                    onChange={(e) => setForm({ ...form, puc_issued_at: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300">{t.growingAreas.expiresAt}</label>
                  <input
                    type="date"
                    value={form.puc_expires_at}
                    onChange={(e) => setForm({ ...form, puc_expires_at: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>
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

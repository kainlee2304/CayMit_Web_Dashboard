"use client";

import React, { useState, useEffect } from "react";
import { getFarms, getGrowingAreas, getFarmers, createFarm, Farm, GrowingArea, FarmerProfile } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { Building2, Plus, Search, RefreshCw, MapPin, UserCheck, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function FarmsPage() {
  const { t } = useLanguage();
  const [farms, setFarms] = useState<Farm[]>([]);
  const [areas, setAreas] = useState<GrowingArea[]>([]);
  const [farmers, setFarmers] = useState<FarmerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New farm form state
  const [form, setForm] = useState({
    farm_code: "",
    farm_name: "",
    growing_area_id: "",
    owner_farmer_user_id: "",
    address_line: "",
    farm_area_hectares: 3.5,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [farmsData, areasData, farmersData] = await Promise.all([
        getFarms(),
        getGrowingAreas(),
        getFarmers(),
      ]);
      setFarms(farmsData);
      setAreas(areasData);
      setFarmers(farmersData);
      if (areasData.length > 0 && !form.growing_area_id) {
        setForm((prev) => ({ ...prev, growing_area_id: areasData[0].id }));
      }
      if (farmersData.length > 0 && !form.owner_farmer_user_id) {
        setForm((prev) => ({ ...prev, owner_farmer_user_id: farmersData[0].id }));
      }
    } catch (err: any) {
      console.error("Failed to load farms:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setMessage(null);
    try {
      await createFarm({
        organization_id: "8a46279f-8b57-47a9-8f6c-50ca2fc61605",
        farm_code: form.farm_code,
        farm_name: form.farm_name,
        growing_area_id: form.growing_area_id,
        owner_farmer_user_id: form.owner_farmer_user_id,
        address_line: form.address_line,
        farm_area_hectares: Number(form.farm_area_hectares),
      });

      setMessage({ type: "success", text: t.farms.addFarm });
      setIsModalOpen(false);
      setForm({
        farm_code: "",
        farm_name: "",
        growing_area_id: areas[0]?.id || "",
        owner_farmer_user_id: farmers[0]?.id || "",
        address_line: "",
        farm_area_hectares: 3.5,
      });
      loadData();
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.response?.data?.error?.details || "Error creating farm.",
      });
    } finally {
      setCreating(false);
    }
  };

  const filteredFarms = farms.filter(
    (f) =>
      f.farm_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.farm_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.address_line?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Building2 className="h-7 w-7 text-emerald-400" />
            {t.farms.title}
          </h1>
          <p className="text-sm text-gray-400 mt-1">{t.farms.subtitle}</p>
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
            {t.farms.addFarm}
          </button>
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

      {/* Farms Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filteredFarms.map((farm) => {
          const matchedArea = areas.find((a) => a.id === farm.growing_area_id);
          const matchedFarmer = farmers.find((f) => f.id === farm.owner_farmer_user_id);

          return (
            <div
              key={farm.id}
              className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur hover:border-gray-700 transition"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  {farm.farm_code}
                </span>
                <span className="text-xs font-bold text-emerald-400">
                  {farm.farm_area_hectares ? `${farm.farm_area_hectares.toFixed(2)} ha` : "—"}
                </span>
              </div>

              <h3 className="text-lg font-bold text-white mt-3">{farm.farm_name}</h3>
              <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-gray-500" />
                {farm.address_line || "Tam Mỹ, Núi Thành, Quảng Nam"}
              </p>

              <div className="mt-4 space-y-2 border-t border-gray-800/60 pt-3 text-xs">
                <div className="flex items-center justify-between text-gray-400">
                  <span>{t.farms.pucAffiliation}:</span>
                  <span className="font-mono font-bold text-white">
                    {matchedArea?.area_code || "PUC-001"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-gray-400">
                  <span>{t.farms.owner}:</span>
                  <span className="font-semibold text-emerald-400">
                    {matchedFarmer?.full_name || "Nông hộ"}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-800/60 flex justify-end">
                <Link
                  href={`/farms/${farm.id}`}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition"
                >
                  {t.common.viewDetails} <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Farm Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Building2 className="h-5 w-5 text-emerald-400" />
              {t.farms.addFarm}
            </h3>
            <p className="text-xs text-gray-400 mt-1">{t.farms.subtitle}</p>

            <form onSubmit={handleCreateFarm} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farms.farmCode} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="FARM-TM-001"
                  value={form.farm_code}
                  onChange={(e) => setForm({ ...form, farm_code: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farms.farmName} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Vườn Mít Ba Tám"
                  value={form.farm_name}
                  onChange={(e) => setForm({ ...form, farm_name: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farms.pucAffiliation} *
                </label>
                <select
                  value={form.growing_area_id}
                  onChange={(e) => setForm({ ...form, growing_area_id: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  {areas.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.area_name} ({a.area_code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farms.owner} *
                </label>
                <select
                  value={form.owner_farmer_user_id}
                  onChange={(e) => setForm({ ...form, owner_farmer_user_id: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                >
                  {farmers.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.full_name} ({f.phone_number})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farms.address}
                </label>
                <input
                  type="text"
                  placeholder="Thôn 1, Xã Tam Mỹ, Núi Thành, Quảng Nam"
                  value={form.address_line}
                  onChange={(e) => setForm({ ...form, address_line: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.common.area} ({t.common.hectares})
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={form.farm_area_hectares}
                  onChange={(e) => setForm({ ...form, farm_area_hectares: parseFloat(e.target.value) || 0 })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
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

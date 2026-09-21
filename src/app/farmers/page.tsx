"use client";

import React, { useState, useEffect } from "react";
import { getFarmers, createFarmer, FarmerProfile } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { Users, UserPlus, Phone, Mail, Building2, Shield, Search, RefreshCw, CheckCircle2, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function FarmersPage() {
  const { t } = useLanguage();
  const [farmers, setFarmers] = useState<FarmerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New farmer form state
  const [form, setForm] = useState({
    username: "",
    full_name_vi: "",
    phone_number: "",
    email: "",
    password: "",
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const data = await getFarmers();
      setFarmers(data);
    } catch (err: any) {
      console.error("Failed to load farmers:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateFarmer = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setMessage(null);
    try {
      await createFarmer({
        organization_id: "8a46279f-8b57-47a9-8f6c-50ca2fc61605",
        username: form.username,
        full_name_vi: form.full_name_vi,
        phone_number: form.phone_number,
        email: form.email || undefined,
        password: form.password || "Farmer@123456",
      });
      setMessage({ type: "success", text: t.farmers.statusActive });
      setIsModalOpen(false);
      setForm({ username: "", full_name_vi: "", phone_number: "", email: "", password: "" });
      loadData();
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.response?.data?.error?.details || "Error creating farmer profile.",
      });
    } finally {
      setCreating(false);
    }
  };

  const filteredFarmers = farmers.filter(
    (f) =>
      f.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.phone_number?.includes(searchTerm) ||
      f.username?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Users className="h-7 w-7 text-emerald-400" />
            {t.farmers.title}
          </h1>
          <p className="text-sm text-gray-400 mt-1">{t.farmers.subtitle}</p>
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
            <UserPlus className="h-4 w-4" />
            {t.farmers.addFarmer}
          </button>
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <p className="text-xs font-medium text-gray-400">{t.dashboard.totalFarmers}</p>
          <p className="mt-2 text-3xl font-bold text-white">{farmers.length}</p>
          <div className="mt-2 flex items-center text-xs text-emerald-400 gap-1 font-semibold">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>{t.farmers.statusActive}</span>
          </div>
        </div>
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <p className="text-xs font-medium text-gray-400">{t.farmers.cooperative}</p>
          <p className="mt-2 text-3xl font-bold text-emerald-400">HTX Tam Mỹ</p>
          <p className="mt-2 text-xs text-gray-500">DataScope: OWN</p>
        </div>
        <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 backdrop-blur">
          <p className="text-xs font-medium text-gray-400">Security & RBAC</p>
          <p className="mt-2 text-xl font-bold text-amber-400">Argon2id + JWT</p>
          <p className="mt-2 text-xs text-gray-500">{t.dashboard.fourEyesNotice}</p>
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

      {/* Filters & Search */}
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

      {/* Farmers List */}
      <div className="rounded-2xl border border-gray-800 bg-gray-900/60 backdrop-blur overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-400">{t.common.loading}</div>
        ) : filteredFarmers.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">{t.common.noData}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="border-b border-gray-800 bg-gray-950/50 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3.5">{t.farmers.fullName}</th>
                  <th className="px-6 py-3.5">{t.farmers.phone}</th>
                  <th className="px-6 py-3.5">{t.farmers.username}</th>
                  <th className="px-6 py-3.5">{t.common.status}</th>
                  <th className="px-6 py-3.5 text-right">{t.common.actions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {filteredFarmers.map((farmer) => (
                  <tr key={farmer.id} className="hover:bg-gray-800/30 transition">
                    <td className="px-6 py-4 font-semibold text-white flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
                        {farmer.full_name?.charAt(0) || "N"}
                      </div>
                      <div>
                        <p>{farmer.full_name}</p>
                        <p className="text-xs text-gray-500">{farmer.email || "—"}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="flex items-center gap-1.5 font-mono text-gray-300">
                        <Phone className="h-3.5 w-3.5 text-gray-500" />
                        {farmer.phone_number}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-400">{farmer.username}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
                        <Shield className="h-3 w-3" />
                        Farmer (OWN)
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href="/farms"
                        className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition"
                      >
                        {t.common.viewDetails} <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Farmer Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-emerald-400" />
              {t.farmers.addFarmer}
            </h3>
            <p className="text-xs text-gray-400 mt-1">{t.farmers.subtitle}</p>

            <form onSubmit={handleCreateFarmer} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farmers.fullName} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Nguyễn Văn Ba"
                  value={form.full_name_vi}
                  onChange={(e) => setForm({ ...form, full_name_vi: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farmers.phone} *
                </label>
                <input
                  type="tel"
                  required
                  placeholder="0901234567"
                  value={form.phone_number}
                  onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farmers.username} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="farmer_batam"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farmers.email}
                </label>
                <input
                  type="email"
                  placeholder="farmer@example.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 px-3.5 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300">
                  {t.farmers.initPassword}
                </label>
                <input
                  type="password"
                  placeholder="Farmer@123456"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
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

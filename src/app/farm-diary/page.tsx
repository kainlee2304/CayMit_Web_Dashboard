"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  getFarmActivities,
  createFarmActivity,
  getSeasons,
  getMasterActivityTypes,
  getMaterials,
  getMaterialBatches,
  FarmActivity,
  CropSeason,
  ActivityType,
  Material,
  MaterialBatch,
} from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import {
  BookOpen,
  Plus,
  Search,
  RefreshCw,
  Sprout,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  MapPin,
  X,
  Layers,
  FlaskConical,
  Camera,
  Sun,
  Cloud,
  CloudRain,
  Wind,
  Upload,
} from "lucide-react";
import Link from "next/link";

export default function FarmDiaryPage() {
  const searchParams = useSearchParams();
  const seasonParam = searchParams.get("season_id");
  const { t, language } = useLanguage();
  const { user } = useAuth();

  const [activities, setActivities] = useState<FarmActivity[]>([]);
  const [seasons, setSeasons] = useState<CropSeason[]>([]);
  const [activityTypes, setActivityTypes] = useState<ActivityType[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [batches, setBatches] = useState<MaterialBatch[]>([]);

  const [loading, setLoading] = useState(true);
  const [selectedSeason, setSelectedSeason] = useState<string>(seasonParam || "ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Form State
  const [form, setForm] = useState({
    season_id: "",
    activity_type_id: "",
    performed_at: new Date().toISOString().slice(0, 16),
    latitude: 15.4235,
    longitude: 108.6235,
    gps_accuracy_meters: 4.5,
    duration_hours: 2.0,
    weather_condition: "SUNNY",
    notes: "",
    material_batch_id: "",
    quantity_applied: 5.0,
    application_method: "FOLIAR_SPRAY",
    evidence_photo_base64: "",
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [actData, seaData, typeData, matData, batData] = await Promise.all([
        getFarmActivities({
          season_id: selectedSeason !== "ALL" ? selectedSeason : undefined,
          verification_status: statusFilter !== "ALL" ? statusFilter : undefined,
        }),
        getSeasons(),
        getMasterActivityTypes(language),
        getMaterials(),
        getMaterialBatches(),
      ]);
      setActivities(actData);
      setSeasons(seaData);
      setActivityTypes(typeData);
      setMaterials(matData);
      setBatches(batData);

      if (seaData.length > 0 && !form.season_id) {
        setForm((prev) => ({ ...prev, season_id: seaData[0].id }));
      }
      if (typeData.length > 0 && !form.activity_type_id) {
        setForm((prev) => ({ ...prev, activity_type_id: typeData[0].id }));
      }
      if (batData.length > 0 && !form.material_batch_id) {
        setForm((prev) => ({ ...prev, material_batch_id: batData[0].id }));
      }
    } catch (err: any) {
      console.error("Failed to load farm diary:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedSeason, statusFilter, language]);

  const selectedActivityType = activityTypes.find((at) => at.id === form.activity_type_id);
  const selectedBatch = batches.find((b) => b.id === form.material_batch_id);

  // Auto-detect Geolocation
  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setForm((prev) => ({
            ...prev,
            latitude: Number(pos.coords.latitude.toFixed(6)),
            longitude: Number(pos.coords.longitude.toFixed(6)),
            gps_accuracy_meters: Number(pos.coords.accuracy.toFixed(1)),
          }));
        },
        (err) => console.warn("Geolocation denied, using default plot coords")
      );
    }
  };

  // Image upload to base64
  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setForm((prev) => ({ ...prev, evidence_photo_base64: reader.result as string }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handleCreateActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setMessage(null);
    try {
      const payload: any = {
        season_id: form.season_id,
        activity_type_id: form.activity_type_id,
        performed_at: new Date(form.performed_at).toISOString(),
        gps_point: {
          type: "Point",
          coordinates: [Number(form.longitude), Number(form.latitude)],
        },
        gps_accuracy_meters: Number(form.gps_accuracy_meters),
        duration_hours: Number(form.duration_hours),
        weather_condition: form.weather_condition,
        notes: form.notes,
        evidence_photo_base64: form.evidence_photo_base64 || undefined,
      };

      // If activity requires material or batch selected
      if (selectedActivityType?.requires_material && form.material_batch_id && selectedBatch) {
        payload.materials = [
          {
            material_batch_id: form.material_batch_id,
            quantity_applied: Number(form.quantity_applied),
            unit_id: selectedBatch.unit_id,
            application_method: form.application_method,
          },
        ];
      }

      await createFarmActivity(payload);
      setMessage({ type: "success", text: language === "vi" ? "Ghi nhật ký canh tác thành công!" : "Activity recorded successfully!" });
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      const errDetail = err.response?.data?.error?.message || err.message || "Failed to record activity";
      setMessage({ type: "error", text: errDetail });
    } finally {
      setCreating(false);
    }
  };

  const filteredActivities = activities.filter((act) => {
    const matchesSearch =
      act.activity_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (act.activity_name_vi || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (act.season_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (act.notes || "").toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

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

  const canCreate = user?.role === "admin_hq" || user?.role === "admin" || user?.role === "farmer" || user?.role === "producer";

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <BookOpen className="h-7 w-7 text-emerald-400" />
            {t.farmDiary.title}
          </h1>
          <p className="text-sm text-gray-400 mt-1">{t.farmDiary.subtitle}</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-gray-700 bg-gray-800/80 px-4 py-2.5 text-xs font-semibold text-gray-200 hover:bg-gray-700 hover:text-white transition disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-emerald-400" : ""}`} />
            {t.common.refresh}
          </button>
          {canCreate && (
            <button
              onClick={() => {
                handleGetLocation();
                setIsModalOpen(true);
              }}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 transition"
            >
              <Plus className="h-4 w-4" />
              {t.farmDiary.addActivity}
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

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder={t.common.search}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-xl border border-gray-800 bg-gray-900/80 py-2.5 pl-10 pr-4 text-xs text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
          {/* Season Filter Dropdown */}
          <select
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value)}
            className="rounded-xl border border-gray-800 bg-gray-900 px-3 py-2 text-xs text-gray-300 focus:border-emerald-500 focus:outline-none"
          >
            <option value="ALL">{language === "vi" ? "Tất cả Mùa Vụ" : "All Seasons"}</option>
            {seasons.map((s) => (
              <option key={s.id} value={s.id}>
                {s.season_name} ({s.plot_name})
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-gray-800 bg-gray-900 px-3 py-2 text-xs text-gray-300 focus:border-emerald-500 focus:outline-none"
          >
            <option value="ALL">{language === "vi" ? "Tất cả Trạng thái" : "All Status"}</option>
            <option value="PENDING">{t.common.pending}</option>
            <option value="VERIFIED">{t.common.verified}</option>
            <option value="REJECTED">{t.common.rejected}</option>
          </select>
        </div>
      </div>

      {/* Activity Timeline List */}
      {loading ? (
        <div className="flex min-h-64 items-center justify-center rounded-2xl border border-gray-800 bg-gray-900/40">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="h-8 w-8 animate-spin text-emerald-500" />
            <span className="text-xs text-gray-400">{t.common.loading}</span>
          </div>
        </div>
      ) : filteredActivities.length === 0 ? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-2xl border border-gray-800 bg-gray-900/40 p-8 text-center">
          <BookOpen className="h-12 w-12 text-gray-600 mb-3" />
          <p className="text-sm font-semibold text-gray-300">{t.common.noData}</p>
          <p className="text-xs text-gray-500 mt-1 max-w-sm">
            {language === "vi" ? "Chưa có nhật ký canh tác nào được ghi nhận." : "No farm diary logs found matching your filters."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredActivities.map((act) => {
            const formattedDate = new Date(act.performed_at).toLocaleString("vi-VN", {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
            });
            return (
              <div
                key={act.id}
                className="group flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-gray-800 bg-gray-900/70 p-5 hover:border-emerald-500/40 hover:bg-gray-900/90 transition shadow-lg shadow-black/20"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <Sprout className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                        {act.activity_code}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          act.verification_status === "VERIFIED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : act.verification_status === "REJECTED"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        {act.verification_status === "VERIFIED" && <CheckCircle2 className="h-3 w-3" />}
                        {act.verification_status === "PENDING" && <Clock className="h-3 w-3" />}
                        {act.verification_status}
                      </span>
                      {act.is_geofence_verified && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          <MapPin className="h-3 w-3" />
                          Geofenced
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-white mt-1.5 group-hover:text-emerald-300 transition">
                      {act.activity_name_vi || act.activity_type_code}
                    </h3>

                    <p className="text-xs text-gray-400 mt-1">{act.notes || "Ghi chép hoạt động chăm sóc cây"}</p>

                    {/* Applied Materials Badges */}
                    {act.materials && act.materials.length > 0 && (
                      <div className="mt-2.5 flex flex-wrap gap-2">
                        {act.materials.map((mat) => (
                          <span
                            key={mat.id}
                            className="inline-flex items-center gap-1.5 text-[11px] font-medium text-gray-300 bg-gray-950/80 border border-gray-800 px-2.5 py-1 rounded-lg"
                          >
                            <FlaskConical className="h-3.5 w-3.5 text-emerald-400" />
                            <b>{mat.material_name || "Phân bón sinh học"}</b>
                            <span className="text-emerald-400 font-bold">{mat.quantity_applied} {mat.unit_code}</span>
                            <span className="text-gray-500 text-[10px]">(PHI: {mat.phi_days_applied}d)</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Meta info & Details Button */}
                <div className="flex items-center justify-between sm:justify-end gap-5 pt-3 sm:pt-0 border-t sm:border-t-0 border-gray-800 text-xs">
                  <div className="space-y-1 text-right">
                    <p className="text-[11px] text-gray-500 flex items-center justify-end gap-1">
                      {getWeatherIcon(act.weather_condition)}
                      {formattedDate}
                    </p>
                    <p className="font-medium text-gray-300">{act.performed_by_name || "Nông hộ Ba Tám"}</p>
                    <p className="text-[11px] text-emerald-400 font-mono">{act.season_name}</p>
                  </div>

                  <Link
                    href={`/farm-diary/${act.id}`}
                    className="flex items-center gap-1.5 rounded-xl border border-gray-700 bg-gray-800 px-4 py-2 text-xs font-semibold text-emerald-400 hover:bg-gray-700 transition"
                  >
                    {t.common.details}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Record Farm Activity Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-xl rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-2xl my-8 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-400 border border-emerald-500/20">
                  <BookOpen className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{t.farmDiary.addActivity}</h3>
                  <p className="text-xs text-gray-400 mt-0.5">{t.farmDiary.subtitle}</p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateActivity} className="mt-4 space-y-4">
              {/* Season Selector */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  {t.seasons.seasonName} *
                </label>
                <select
                  value={form.season_id}
                  onChange={(e) => setForm({ ...form, season_id: e.target.value })}
                  required
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
                >
                  {seasons.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.season_name} ({s.plot_name})
                    </option>
                  ))}
                </select>
              </div>

              {/* Activity Type */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  {t.farmDiary.activityType} *
                </label>
                <select
                  value={form.activity_type_id}
                  onChange={(e) => setForm({ ...form, activity_type_id: e.target.value })}
                  required
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
                >
                  {activityTypes.map((at) => (
                    <option key={at.id} value={at.id}>
                      {language === "vi" ? at.name_vi : at.name_en} ({at.activity_code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Date/Time, Duration & Weather */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1.5">
                    {t.farmDiary.performedAt} *
                  </label>
                  <input
                    type="datetime-local"
                    value={form.performed_at}
                    onChange={(e) => setForm({ ...form, performed_at: e.target.value })}
                    required
                    className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1.5">
                    {t.farmDiary.durationHours}
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="12"
                    value={form.duration_hours}
                    onChange={(e) => setForm({ ...form, duration_hours: Number(e.target.value) })}
                    className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1.5">
                    {t.farmDiary.weather}
                  </label>
                  <select
                    value={form.weather_condition}
                    onChange={(e) => setForm({ ...form, weather_condition: e.target.value })}
                    className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="SUNNY">{t.farmDiary.weatherSunny}</option>
                    <option value="CLOUDY">{t.farmDiary.weatherCloudy}</option>
                    <option value="RAINY">{t.farmDiary.weatherRainy}</option>
                    <option value="WINDY">{t.farmDiary.weatherWindy}</option>
                  </select>
                </div>
              </div>

              {/* GPS Coordinates Geofencing */}
              <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-emerald-400" />
                    {t.farmDiary.gpsStatus}
                  </span>
                  <button
                    type="button"
                    onClick={handleGetLocation}
                    className="text-[11px] font-semibold text-emerald-400 hover:underline"
                  >
                    Lấy tọa độ hiện tại
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[10px] text-gray-500">Vĩ độ (Lat):</span>
                    <input
                      type="number"
                      step="0.000001"
                      value={form.latitude}
                      onChange={(e) => setForm({ ...form, latitude: Number(e.target.value) })}
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1 text-xs text-white"
                    />
                  </div>
                  <div>
                    <span className="text-[10px] text-gray-500">Kinh độ (Lng):</span>
                    <input
                      type="number"
                      step="0.000001"
                      value={form.longitude}
                      onChange={(e) => setForm({ ...form, longitude: Number(e.target.value) })}
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1 text-xs text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Material Usage Row (If activity uses materials) */}
              {selectedActivityType?.requires_material && (
                <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-3 space-y-3">
                  <span className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                    <FlaskConical className="h-3.5 w-3.5 text-emerald-400" />
                    {t.farmDiary.materialsApplied}
                  </span>

                  <div className="space-y-2">
                    <div>
                      <label className="block text-[11px] text-gray-400 mb-1">
                        {t.farmDiary.materialBatch} *
                      </label>
                      <select
                        value={form.material_batch_id}
                        onChange={(e) => setForm({ ...form, material_batch_id: e.target.value })}
                        required
                        className="w-full rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
                      >
                        {batches.map((b) => (
                          <option key={b.id} value={b.id}>
                            {b.material_name} - Lô {b.batch_number} (Tồn: {b.remaining_quantity} {b.unit_code})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[11px] text-gray-400 mb-1">
                          {t.farmDiary.dosageApplied} ({selectedBatch?.unit_code || "kg/lít"}) *
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          min="0.1"
                          value={form.quantity_applied}
                          onChange={(e) => setForm({ ...form, quantity_applied: Number(e.target.value) })}
                          required
                          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-white"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] text-gray-400 mb-1">
                          {t.farmDiary.applicationMethod}
                        </label>
                        <select
                          value={form.application_method}
                          onChange={(e) => setForm({ ...form, application_method: e.target.value })}
                          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-white"
                        >
                          <option value="FOLIAR_SPRAY">{t.farmDiary.foliarSpray}</option>
                          <option value="ROOT_FERTILIZE">{t.farmDiary.rootFertilize}</option>
                          <option value="SOIL_DRENCH">{t.farmDiary.soilDrench}</option>
                          <option value="DUSTING">{t.farmDiary.dusting}</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Evidence Photo Upload */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  {t.farmDiary.evidencePhoto}
                </label>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 cursor-pointer rounded-xl border border-gray-700 bg-gray-800 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-700">
                    <Camera className="h-4 w-4 text-emerald-400" />
                    <span>Chọn ảnh hiện trường</span>
                    <input type="file" accept="image/*" onChange={handlePhotoUpload} className="hidden" />
                  </label>
                  {form.evidence_photo_base64 && (
                    <span className="text-xs text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Đã đính kèm ảnh
                    </span>
                  )}
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Ghi chú canh tác & Liều lượng thực tế
                </label>
                <textarea
                  rows={2}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="Ghi chú chi tiết kỹ thuật canh tác..."
                  className="w-full rounded-xl border border-gray-700 bg-gray-800 px-3 py-2 text-xs text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* Modal Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl border border-gray-700 bg-gray-800 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-gray-700"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                >
                  {creating && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                  {t.farmDiary.addActivity}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

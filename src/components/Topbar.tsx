"use client";

import React, { useState, useEffect, useRef } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth, ROLE_LABELS } from "@/context/AuthContext";
import { globalSearch, GlobalSearchResult } from "@/lib/api";
import {
  Search,
  Globe,
  Building2,
  Users,
  ShieldCheck,
  MapPin,
  LogOut,
  X,
  ExternalLink,
  ChevronDown,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function Topbar() {
  const { locale, setLocale, t } = useLanguage();
  const { user, logout } = useAuth();
  const router = useRouter();

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GlobalSearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  // Close search dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setSearchResults(null);
      setIsDropdownOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setSearching(true);
        const res = await globalSearch(query.trim());
        setSearchResults(res);
        setIsDropdownOpen(true);
      } catch (err) {
        console.error("Global search failed:", err);
      } finally {
        setSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelectResult = (url: string) => {
    setIsDropdownOpen(false);
    setQuery("");
    router.push(url);
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-gray-800 bg-gray-950/90 px-4 sm:px-6 backdrop-blur font-sans">
      {/* Search Bar */}
      <div ref={searchRef} className="relative w-72 sm:w-96">
        <div className="relative flex items-center">
          <Search className="absolute left-3.5 h-4 w-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            placeholder={t.topbar.searchPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => query.length >= 2 && setIsDropdownOpen(true)}
            className="w-full rounded-xl border border-gray-800 bg-gray-900/90 pl-10 pr-8 py-2 text-xs text-white placeholder-gray-500 outline-none focus:border-emerald-500 transition"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setIsDropdownOpen(false);
              }}
              className="absolute right-2.5 text-gray-500 hover:text-white"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Global Search Results Dropdown */}
        {isDropdownOpen && searchResults && (
          <div className="absolute left-0 right-0 top-12 z-50 max-h-96 overflow-y-auto rounded-2xl border border-gray-800 bg-gray-900 p-3 shadow-2xl backdrop-blur">
            <div className="mb-2 flex items-center justify-between px-2 text-[11px] font-semibold text-gray-400 border-b border-gray-800 pb-1.5">
              <span>{t.common.search}: "{query}"</span>
              <span className="text-emerald-400">{searchResults.total_matches} {t.common.allResultsCount}</span>
            </div>

            {searchResults.total_matches === 0 ? (
              <p className="p-3 text-center text-xs text-gray-500">{t.common.noData}</p>
            ) : (
              <div className="space-y-3 text-xs">
                {/* Farmers */}
                {searchResults.farmers?.length > 0 && (
                  <div>
                    <p className="px-2 py-1 font-bold text-gray-400 flex items-center gap-1.5 uppercase text-[10px]">
                      <Users className="h-3 w-3 text-emerald-400" /> {t.farmers.title}
                    </p>
                    {searchResults.farmers.map((f) => (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => handleSelectResult("/farmers")}
                        className="w-full text-left rounded-lg px-2.5 py-1.5 hover:bg-gray-800 flex items-center justify-between text-gray-300 hover:text-white transition"
                      >
                        <span className="font-semibold">{f.full_name}</span>
                        <span className="font-mono text-[11px] text-gray-500">{f.phone_number}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Growing Areas */}
                {searchResults.growing_areas?.length > 0 && (
                  <div>
                    <p className="px-2 py-1 font-bold text-gray-400 flex items-center gap-1.5 uppercase text-[10px]">
                      <ShieldCheck className="h-3 w-3 text-emerald-400" /> {t.growingAreas.title}
                    </p>
                    {searchResults.growing_areas.map((ga) => (
                      <button
                        key={ga.id}
                        type="button"
                        onClick={() => handleSelectResult(`/growing-areas/${ga.id}`)}
                        className="w-full text-left rounded-lg px-2.5 py-1.5 hover:bg-gray-800 flex items-center justify-between text-gray-300 hover:text-white transition"
                      >
                        <span className="font-semibold">{ga.area_name}</span>
                        <span className="font-mono text-[11px] text-emerald-400">{ga.area_code}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Farms */}
                {searchResults.farms?.length > 0 && (
                  <div>
                    <p className="px-2 py-1 font-bold text-gray-400 flex items-center gap-1.5 uppercase text-[10px]">
                      <Building2 className="h-3 w-3 text-emerald-400" /> {t.farms.title}
                    </p>
                    {searchResults.farms.map((farm) => (
                      <button
                        key={farm.id}
                        type="button"
                        onClick={() => handleSelectResult(`/farms/${farm.id}`)}
                        className="w-full text-left rounded-lg px-2.5 py-1.5 hover:bg-gray-800 flex items-center justify-between text-gray-300 hover:text-white transition"
                      >
                        <span className="font-semibold">{farm.farm_name}</span>
                        <span className="font-mono text-[11px] text-amber-400">{farm.farm_code}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Plots */}
                {searchResults.plots?.length > 0 && (
                  <div>
                    <p className="px-2 py-1 font-bold text-gray-400 flex items-center gap-1.5 uppercase text-[10px]">
                      <MapPin className="h-3 w-3 text-emerald-400" /> {t.plots.title}
                    </p>
                    {searchResults.plots.map((plot) => (
                      <button
                        key={plot.id}
                        type="button"
                        onClick={() => handleSelectResult(`/plots/${plot.id}`)}
                        className="w-full text-left rounded-lg px-2.5 py-1.5 hover:bg-gray-800 flex items-center justify-between text-gray-300 hover:text-white transition"
                      >
                        <span className="font-semibold">{plot.plot_name}</span>
                        <span className="font-mono text-[11px] text-emerald-400">{plot.plot_code}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Controls: Active Org + Language Switcher + User Info */}
      <div className="flex items-center gap-3">
        {/* Active Organization Pill */}
        <div className="hidden md:flex items-center gap-1.5 rounded-xl border border-gray-800 bg-gray-900/80 px-3 py-1.5 text-xs text-gray-300">
          <Building2 className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-gray-500">{t.topbar.activeOrg}</span>
          <span className="font-bold text-white">{user?.organization || "HTX Tam Mỹ"}</span>
        </div>

        {/* Language Switcher: VI | EN Toggle */}
        <div className="flex items-center rounded-xl border border-gray-800 bg-gray-900 p-1 shadow-inner">
          <button
            type="button"
            onClick={() => setLocale("vi")}
            className={`rounded-lg px-2.5 py-1 text-xs font-bold transition-all ${
              locale === "vi"
                ? "bg-emerald-500 text-white shadow-md shadow-emerald-500/20"
                : "text-gray-400 hover:text-white"
            }`}
            title="Chuyển sang Tiếng Việt"
          >
            🇻🇳 VI
          </button>
          <button
            type="button"
            onClick={() => setLocale("en")}
            className={`rounded-lg px-2.5 py-1 text-xs font-bold transition-all ${
              locale === "en"
                ? "bg-emerald-500 text-white shadow-md shadow-emerald-500/20"
                : "text-gray-400 hover:text-white"
            }`}
            title="Switch to English"
          >
            🇬🇧 EN
          </button>
        </div>

        {/* User Profile / Logout Quick Pill */}
        {user && (
          <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-gray-800">
            <div className="text-right">
              <p className="text-xs font-bold text-white leading-tight">{user.display_name}</p>
              <p className="text-[10px] text-emerald-400 font-semibold">{t.roles[user.role as keyof typeof t.roles] || user.role}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                logout();
                window.location.href = "/login";
              }}
              className="rounded-xl border border-gray-800 bg-gray-900 p-2 text-gray-400 hover:text-rose-400 hover:border-rose-500/30 transition"
              title={t.nav.logout}
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

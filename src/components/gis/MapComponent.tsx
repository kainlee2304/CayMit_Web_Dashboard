"use client";

import React, { useEffect, useRef, useState } from "react";
import { GeoJSONGeometry } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { Layers, MapPin, ShieldCheck, Compass, Eye, AlertTriangle } from "lucide-react";
import "leaflet/dist/leaflet.css";

export interface MapFeature {
  id: string;
  name: string;
  code: string;
  type: "PUC" | "PLOT";
  geometry?: GeoJSONGeometry;
  status?: string;
  area_ha?: number;
  highlighted?: boolean;
  metadata?: Record<string, any>;
}

interface MapComponentProps {
  features?: MapFeature[];
  selectedFeatureId?: string;
  onSelectFeature?: (feature: MapFeature) => void;
  gpsPin?: { lat: number; lng: number; label?: string; accuracy_m?: number };
  height?: string;
  showControls?: boolean;
}

export default function MapComponent({
  features = [],
  selectedFeatureId,
  onSelectFeature,
  gpsPin,
  height = "450px",
  showControls = true,
}: MapComponentProps) {
  const { t } = useLanguage();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const layersGroupRef = useRef<any>(null);
  const gpsLayerRef = useRef<any>(null);

  const [showPucLayer, setShowPucLayer] = useState(true);
  const [showPlotLayer, setShowPlotLayer] = useState(true);
  const [mapReady, setMapReady] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState<MapFeature | null>(null);

  // Initialize Leaflet Map instance
  useEffect(() => {
    if (typeof window === "undefined" || !mapContainerRef.current) return;

    let isMounted = true;

    const initMap = async () => {
      const L = (await import("leaflet")).default;

      if (!mapContainerRef.current) return;

      // Fix default marker icons in Leaflet
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      if (!mapInstanceRef.current && isMounted) {
        // Default center: Tam My, Nui Thanh, Quang Nam [15.4230, 108.6230]
        const map = L.map(mapContainerRef.current, {
          center: [15.423, 108.623],
          zoom: 14,
          zoomControl: false,
        });

        // Add standard OpenStreetMap tiles
        const standardTile = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          maxZoom: 19,
        });
        standardTile.addTo(map);

        // Zoom control on top right
        L.control.zoom({ position: "topright" }).addTo(map);

        const featureGroup = L.featureGroup().addTo(map);
        const gpsGroup = L.layerGroup().addTo(map);

        mapInstanceRef.current = map;
        layersGroupRef.current = featureGroup;
        gpsLayerRef.current = gpsGroup;

        if (isMounted) setMapReady(true);
      }
    };

    initMap();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update GeoJSON Layers whenever features, layers toggle, or selectedFeatureId changes
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || !layersGroupRef.current) return;

    const updateLayers = async () => {
      const L = (await import("leaflet")).default;
      const group = layersGroupRef.current;
      group.clearLayers();

      let hasValidGeom = false;

      features.forEach((feature) => {
        if (!feature.geometry || !feature.geometry.coordinates) return;

        const isPuc = feature.type === "PUC";
        const isPlot = feature.type === "PLOT";

        if (isPuc && !showPucLayer) return;
        if (isPlot && !showPlotLayer) return;

        const isSelected = feature.id === selectedFeatureId;

        // Custom Leaflet styling for PostGIS Polygons
        const style = isPuc
          ? {
              color: isSelected ? "#10b981" : "#059669",
              weight: isSelected ? 3.5 : 2,
              fillColor: isSelected ? "#10b981" : "#059669",
              fillOpacity: isSelected ? 0.35 : 0.15,
              dashArray: feature.status === "SUSPENDED" ? "6, 6" : undefined,
            }
          : {
              color: isSelected ? "#f59e0b" : "#3b82f6",
              weight: isSelected ? 3.5 : 2,
              fillColor: isSelected ? "#f59e0b" : "#3b82f6",
              fillOpacity: isSelected ? 0.4 : 0.2,
            };

        try {
          const geoJsonLayer = L.geoJSON(feature.geometry as any, {
            style,
            onEachFeature: (_, layer) => {
              layer.on({
                click: () => {
                  setSelectedFeature(feature);
                  if (onSelectFeature) onSelectFeature(feature);
                },
                mouseover: (e) => {
                  const l = e.target;
                  l.setStyle({ weight: 4, fillOpacity: 0.5 });
                },
                mouseout: (e) => {
                  const l = e.target;
                  l.setStyle(style);
                },
              });

              // Popup content
              const popupContent = `
                <div style="font-family: sans-serif; font-size: 12px; color: #111827; min-width: 160px;">
                  <div style="font-weight: bold; font-size: 13px; color: #047857; margin-bottom: 2px;">
                    ${feature.name}
                  </div>
                  <div style="font-family: monospace; font-size: 11px; color: #4b5563;">
                    ${t.common.code}: <b>${feature.code}</b>
                  </div>
                  ${
                    feature.area_ha
                      ? `<div style="font-size: 11px; color: #059669; margin-top: 2px;">
                          ${t.common.area}: <b>${feature.area_ha.toFixed(2)} ha</b>
                        </div>`
                      : ""
                  }
                  ${
                    feature.status
                      ? `<div style="font-size: 10px; margin-top: 3px; font-weight: bold;">
                          ${t.common.status}: <span style="color: ${
                            feature.status === "ACTIVE" ? "#059669" : "#d97706"
                          }">${feature.status}</span>
                        </div>`
                      : ""
                  }
                </div>
              `;
              layer.bindPopup(popupContent);
            },
          });

          geoJsonLayer.addTo(group);
          hasValidGeom = true;
        } catch (err) {
          console.error("Leaflet GeoJSON parsing error for feature:", feature.code, err);
        }
      });

      // Fit bounds if valid geometries exist
      if (hasValidGeom && group.getBounds().isValid()) {
        mapInstanceRef.current.fitBounds(group.getBounds(), { padding: [30, 30], maxZoom: 16 });
      }
    };

    updateLayers();
  }, [features, mapReady, showPucLayer, showPlotLayer, selectedFeatureId, t]);

  // Update GPS Evidence Pin
  useEffect(() => {
    if (!mapReady || !gpsLayerRef.current) return;

    const updateGps = async () => {
      const L = (await import("leaflet")).default;
      const group = gpsLayerRef.current;
      group.clearLayers();

      if (gpsPin && typeof gpsPin.lat === "number" && typeof gpsPin.lng === "number") {
        const accuracyCircle = L.circle([gpsPin.lat, gpsPin.lng], {
          radius: gpsPin.accuracy_m || 15,
          color: "#ef4444",
          fillColor: "#ef4444",
          fillOpacity: 0.2,
          weight: 1.5,
        });
        accuracyCircle.addTo(group);

        const gpsIcon = L.divIcon({
          className: "custom-gps-pin",
          html: `
            <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 24px; height: 24px;">
              <div style="position: absolute; width: 24px; height: 24px; border-radius: 9999px; background-color: rgba(239, 68, 68, 0.4); animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
              <div style="position: relative; width: 14px; height: 14px; border-radius: 9999px; background-color: #ef4444; border: 2px solid white; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5);"></div>
            </div>
          `,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });

        const marker = L.marker([gpsPin.lat, gpsPin.lng], { icon: gpsIcon });
        marker.bindPopup(`
          <div style="font-family: sans-serif; font-size: 12px;">
            <b style="color: #dc2626;">📍 ${gpsPin.label || t.gis.gpsPoint}</b>
            <div style="font-size: 11px; color: #4b5563; font-family: monospace; margin-top: 2px;">
              [${gpsPin.lat.toFixed(5)}, ${gpsPin.lng.toFixed(5)}]
            </div>
          </div>
        `);
        marker.addTo(group);
      }
    };

    updateGps();
  }, [gpsPin, mapReady, t]);

  // Sync selected feature from props
  useEffect(() => {
    if (selectedFeatureId) {
      const found = features.find((f) => f.id === selectedFeatureId);
      if (found) setSelectedFeature(found);
    }
  }, [selectedFeatureId, features]);

  return (
    <div
      className="relative w-full overflow-hidden rounded-2xl border border-gray-800 bg-gray-950 font-sans shadow-2xl"
      style={{ height }}
    >
      {/* Real Leaflet Map Container */}
      <div ref={mapContainerRef} className="h-full w-full z-0" />

      {/* Floating Map Controls on Top Left */}
      {showControls && (
        <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-xl bg-gray-900/90 p-1.5 backdrop-blur border border-gray-800 shadow-xl">
            <button
              type="button"
              onClick={() => setShowPucLayer(!showPucLayer)}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                showPucLayer
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              {t.gis.pucLayer}
            </button>
            <button
              type="button"
              onClick={() => setShowPlotLayer(!showPlotLayer)}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-bold transition ${
                showPlotLayer
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <MapPin className="h-3.5 w-3.5" />
              {t.gis.plotLayer}
            </button>
          </div>

          <div className="flex items-center gap-1.5 rounded-xl bg-gray-900/90 px-3 py-1.5 text-xs text-gray-300 backdrop-blur border border-gray-800 shadow-xl">
            <Compass className="h-3.5 w-3.5 text-emerald-400 animate-spin" style={{ animationDuration: "14s" }} />
            <span className="font-semibold text-[11px]">PostGIS WGS84 (EPSG:4326)</span>
          </div>
        </div>
      )}

      {/* Selected Feature Bottom Summary Banner */}
      {selectedFeature && (
        <div className="absolute bottom-3 left-3 right-3 z-10 flex items-center justify-between rounded-xl bg-gray-900/95 p-3 backdrop-blur border border-gray-800 shadow-2xl">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                selectedFeature.type === "PUC"
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
              }`}
            >
              {selectedFeature.type === "PUC" ? (
                <ShieldCheck className="h-5 w-5" />
              ) : (
                <MapPin className="h-5 w-5" />
              )}
            </div>
            <div>
              <p className="text-xs font-bold text-white">{selectedFeature.name}</p>
              <p className="text-[11px] text-gray-400">
                {t.common.code}: <span className="font-mono text-emerald-400 font-bold">{selectedFeature.code}</span>
                {selectedFeature.area_ha && (
                  <span className="ml-2 font-medium text-gray-300">
                    • {selectedFeature.area_ha.toFixed(2)} ha
                  </span>
                )}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => onSelectFeature && onSelectFeature(selectedFeature)}
            className="flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-white shadow hover:bg-emerald-600 transition"
          >
            <Eye className="h-3.5 w-3.5" />
            {t.common.details}
          </button>
        </div>
      )}
    </div>
  );
}

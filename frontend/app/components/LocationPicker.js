"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import "leaflet/dist/leaflet.css";

import { MapContainer, TileLayer, CircleMarker, useMapEvents } from "react-leaflet";

function LocationMarker({ position, setPosition }) {
  const map = useMapEvents({
    click(e) {
      setPosition(e.latlng);
    },
  });

  return position === null ? null : (
    <CircleMarker
      center={position}
      radius={8}
      pathOptions={{ color: '#059669', fillColor: '#10b981', fillOpacity: 0.8, weight: 3 }}
    ></CircleMarker>
  );
}

export default function LocationPicker({
  isOpen,
  onClose,
  onSelect,
  initialLat,
  initialLon,
}) {
  const [position, setPosition] = useState(
    initialLat && initialLon ? { lat: initialLat, lng: initialLon } : null
  );
  const [soilType, setSoilType] = useState("");
  const [loadingSoil, setLoadingSoil] = useState(false);

  useEffect(() => {
    if (initialLat && initialLon) {
      setPosition({ lat: initialLat, lng: initialLon });
    }
  }, [initialLat, initialLon, isOpen]);

  // Fetch dominant soil type when position changes
  useEffect(() => {
    if (position) {
      setLoadingSoil(true);
      fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/soil/${position.lat}/${position.lng}`)
        .then((r) => r.json())
        .then((data) => {
          setSoilType(data.soil_type || "N/A");
          setLoadingSoil(false);
        })
        .catch(() => {
          setSoilType("N/A");
          setLoadingSoil(false);
        });
    }
  }, [position]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center',
      backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', padding: '16px'
    }}>
      <div style={{
        backgroundColor: '#111a16', border: '1px solid rgba(52, 211, 153, 0.2)', borderRadius: '16px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)', width: '100%', maxWidth: '800px', overflow: 'hidden',
        display: 'flex', flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderBottom: '1px solid rgba(52, 211, 153, 0.1)' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
            <span>📍</span> Select Field Location
          </h2>
          <button
            onClick={onClose}
            style={{ color: '#a7c4b8', fontSize: '1.5rem', fontWeight: 'bold', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>

        {/* Map Area */}
        <div style={{ height: '60vh', width: '100%', position: 'relative' }}>
          <MapContainer
            center={position || { lat: 11.1271, lng: 78.6569 }}
            zoom={position ? 12 : 7}
            style={{ height: "100%", width: "100%", zIndex: 0 }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <LocationMarker position={position} setPosition={setPosition} />
          </MapContainer>
          
          <div style={{
            position: 'absolute', bottom: '16px', left: '16px', zIndex: 400, backgroundColor: 'rgba(10,15,13,0.9)',
            backdropFilter: 'blur(8px)', padding: '12px', borderRadius: '12px', border: '1px solid rgba(52,211,153,0.2)',
            boxShadow: '0 4px 16px rgba(0,0,0,0.4)', fontSize: '0.875rem', color: '#a7c4b8'
          }}>
            Click anywhere on the map to drop a pin.
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: '16px', borderTop: '1px solid rgba(52, 211, 153, 0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'rgba(17,26,22,0.5)', flexWrap: 'wrap', gap: '16px' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ fontSize: '0.875rem', fontFamily: 'monospace', color: '#34d399' }}>
              {position ? `${position.lat.toFixed(4)}, ${position.lng.toFixed(4)}` : "No location selected"}
            </div>
            {position && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#a7c4b8', fontSize: '0.8rem' }}>Soil Type:</span>
                {loadingSoil ? (
                  <span style={{ color: '#fbbf24', fontSize: '0.8rem' }}>Detecting...</span>
                ) : (
                  <select 
                    value={soilType}
                    onChange={(e) => setSoilType(e.target.value)}
                    style={{ 
                      backgroundColor: 'rgba(52, 211, 153, 0.1)', color: '#34d399', 
                      border: '1px solid rgba(52, 211, 153, 0.3)', borderRadius: '4px', 
                      padding: '2px 8px', fontSize: '0.8rem', outline: 'none'
                    }}
                  >
                    <option value="N/A">N/A — no verified soil profile</option>
                    <option value="Red Soil">Red Soil (Alfisol)</option>
                    <option value="Black Soil">Black Soil (Vertisol)</option>
                    <option value="Alluvial Soil">Alluvial Soil (Entisol)</option>
                    <option value="Laterite Soil">Laterite Soil</option>
                    <option value="Coastal Sandy Soil">Coastal Sandy Soil</option>
                  </select>
                )}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={onClose}
              style={{ padding: '8px 16px', borderRadius: '8px', fontSize: '0.875rem', fontWeight: '500', color: '#a7c4b8', background: 'none', border: 'none', cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              onClick={() => {
                if (position) {
                  onSelect(position.lat, position.lng, soilType);
                  onClose();
                }
              }}
              disabled={!position || loadingSoil}
              style={{
                padding: '8px 24px', borderRadius: '8px', fontSize: '0.875rem', fontWeight: 'bold',
                backgroundColor: (position && !loadingSoil) ? '#10b981' : '#047857', color: '#fff', border: 'none',
                cursor: (position && !loadingSoil) ? 'pointer' : 'not-allowed', opacity: (position && !loadingSoil) ? 1 : 0.5,
                boxShadow: (position && !loadingSoil) ? '0 0 15px rgba(16,185,129,0.3)' : 'none'
              }}
            >
              Confirm Location & Soil
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

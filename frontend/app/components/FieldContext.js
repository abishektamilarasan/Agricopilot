"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

const FieldContext = createContext();

export function FieldProvider({ children }) {
  const [lat, setLat] = useState(11.1271);
  const [lon, setLon] = useState(78.6569);
  const [crop, setCrop] = useState("rice");
  const [soilType, setSoilType] = useState("");
  const [fieldSizeHa, setFieldSizeHa] = useState("1");
  const [isLoaded, setIsLoaded] = useState(false);

  // Load from session storage on mount
  useEffect(() => {
    const saved = sessionStorage.getItem("agricopilot_context");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.lat) setLat(parsed.lat);
        if (parsed.lon) setLon(parsed.lon);
        if (parsed.crop) setCrop(parsed.crop);
        if (parsed.soilType) setSoilType(parsed.soilType);
        if (parsed.fieldSizeHa) setFieldSizeHa(parsed.fieldSizeHa);
      } catch (e) {
        console.error("Failed to parse field context", e);
      }
    }
    setIsLoaded(true);
  }, []);

  // Save to session storage when values change
  useEffect(() => {
    if (isLoaded) {
      sessionStorage.setItem("agricopilot_context", JSON.stringify({
        lat, lon, crop, soilType, fieldSizeHa
      }));
    }
  }, [lat, lon, crop, soilType, fieldSizeHa, isLoaded]);

  return (
    <FieldContext.Provider value={{
      lat, setLat,
      lon, setLon,
      crop, setCrop,
      soilType, setSoilType,
      fieldSizeHa, setFieldSizeHa
    }}>
      {children}
    </FieldContext.Provider>
  );
}

export function useFieldContext() {
  const context = useContext(FieldContext);
  if (context === undefined) {
    throw new Error("useFieldContext must be used within a FieldProvider");
  }
  return context;
}

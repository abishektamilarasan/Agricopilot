"use client";



import { useState, useEffect, useCallback } from "react";

import dynamic from "next/dynamic";

import { useFieldContext } from "./components/FieldContext";



const LocationPicker = dynamic(() => import("./components/LocationPicker"), { ssr: false });

const ForecastersPanel = dynamic(() => import("./components/ForecastersPanel").then(m => ({ default: m.ForecastersPanel })), { ssr: false });



const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";



function ConfidenceGauge({ value = 0, size = 120 }) {

  const r = (size - 16) / 2;

  const circ = 2 * Math.PI * r;

  const offset = circ - (value / 100) * circ;

  const color = value >= 70 ? "var(--color-emerald-400)" : value >= 40 ? "var(--color-amber-400)" : "var(--color-red-400)";

  return (

    <div className="confidence-gauge">

      <div className="gauge-circle" style={{ width: size, height: size }}>

        <svg width={size} height={size}>

          <circle className="gauge-bg" cx={size / 2} cy={size / 2} r={r} />

          <circle className="gauge-fill" cx={size / 2} cy={size / 2} r={r}

            style={{ stroke: color, strokeDasharray: circ, strokeDashoffset: offset }} />

        </svg>

        <div className="gauge-value">

          {Math.round(value)}%

          <span className="gauge-label">confidence</span>

        </div>

      </div>

    </div>

  );

}



function MetricBar({ value, max = 100, color = "" }) {

  const pct = Math.min((value / max) * 100, 100);

  return (

    <div className="metric-bar">

      <div className={`metric-bar-fill ${color}`} style={{ width: `${pct}%` }} />

    </div>

  );

}



function RecommendationCard({ rec }) {

  const icons = {
    yield: "🌱",
    irrigation: "💧",
    fertilizer: "🧪",
    disease: "🩺",
    harvest: "🌾",
    market: "📊",
    general: "💡",
  };

  return (

    <div className={`rec-card priority-${rec.priority}`}>

      <div className="rec-header">

        <span className="rec-category">

          {icons[rec.category] || "💡"} {rec.category}

        </span>

        <span className="rec-confidence">{Math.round(rec.confidence)}%</span>

      </div>

      <h4 className="rec-title">{rec.title}</h4>

      <p className="rec-description">{rec.description}</p>

      {rec.reasoning && <p className="rec-reasoning">{rec.reasoning}</p>}

      {rec.data_sources_used?.length > 0 && (

        <div className="rec-sources">

          {rec.data_sources_used.map((src, i) => (

            <span key={i} className="rec-source-tag">{src}</span>

          ))}

        </div>

      )}

    </div>

  );

}



export default function DashboardPage() {

  const { lat, setLat, lon, setLon, crop, setCrop, soilType, setSoilType, fieldSizeHa, setFieldSizeHa } = useFieldContext();



  const [data, setData] = useState(null);

  const [riskData, setRiskData] = useState(null);

  const [loading, setLoading] = useState(false);

  const [riskLoading, setRiskLoading] = useState(false);

  const [error, setError] = useState(null);

  const [apiConnected, setApiConnected] = useState(false);

  const [manualMarketPrice, setManualMarketPrice] = useState("");

  const [isMapOpen, setIsMapOpen] = useState(false);

  const [activeTab, setActiveTab] = useState("overview");



  const [mlParams, setMlParams] = useState({

    N: 0, P: 0, K: 0, pH: 6.5, EC: 0, OC: 0, S: 0, Zn: 0, Fe: 0, Cu: 0, Mn: 0, B: 0,

    temp: 25, humidity: 60, rainfall: 100

  });

  const [mlCropResult, setMlCropResult] = useState(null);

  const [mlSoilResult, setMlSoilResult] = useState(null);

  const [mlLoading, setMlLoading] = useState(false);



  useEffect(() => {

    fetch(`${API_BASE}/api/health`)

      .then((r) => r.json())

      .then(() => {

        setApiConnected(true);

        const dot = document.getElementById("status-indicator");

        const txt = document.getElementById("status-text");

        if (dot) dot.classList.remove("offline");

        if (txt) txt.textContent = "Connected";

      })

      .catch(() => {

        setApiConnected(false);

        const dot = document.getElementById("status-indicator");

        const txt = document.getElementById("status-text");

        if (dot) dot.classList.add("offline");

        if (txt) txt.textContent = "Backend offline";

      });

  }, []);



  const [fromCache, setFromCache] = useState(false);



  const runAnalysis = useCallback(async (forceRefresh = false) => {

    setLoading(true);

    setError(null);

    setFromCache(false);



    const cacheKey = `agricopilot_${parseFloat(lat).toFixed(4)}_${parseFloat(lon).toFixed(4)}_${crop}`;



    if (!forceRefresh) {

      try {

        const cached = sessionStorage.getItem(cacheKey);

        if (cached) {

          const parsed = JSON.parse(cached);

          setData(parsed);

          setFromCache(true);

          setLoading(false);

          autoFillMlParams(parsed);

          return;

        }

      } catch (_) { }

    }



    try {

      const resp = await fetch(`${API_BASE}/api/analyze`, {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({

          latitude: parseFloat(lat), longitude: parseFloat(lon),

          crop, country: "India",

          field_size_ha: parseFloat(fieldSizeHa) || undefined,

          manual_market_price: parseFloat(manualMarketPrice) || undefined,

        }),

      });

      if (!resp.ok) throw new Error(`API error: ${resp.status}`);

      const result = await resp.json();

      setData(result);

      setFromCache(false);

      autoFillMlParams(result);

      try { sessionStorage.setItem(cacheKey, JSON.stringify(result)); } catch (_) {}

    } catch (e) {

      setError(e.message);

    } finally {

      setLoading(false);

    }

  }, [lat, lon, crop, fieldSizeHa, manualMarketPrice]);



  function autoFillMlParams(result) {

    setMlParams(p => ({

      ...p,

      N: result.soil?.nitrogen_g_kg || p.N,

      pH: result.soil?.ph || p.pH,

      OC: result.soil?.organic_carbon_g_kg || p.OC,

      temp: result.weather?.temperature_current || p.temp,

      humidity: result.weather?.humidity || p.humidity,

      rainfall: result.weather?.precipitation_mm || p.rainfall,

    }));

  }



  const fetchRiskData = async () => {

    setRiskLoading(true);

    try {

      const resp = await fetch(`${API_BASE}/api/risk-dashboard`, {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ latitude: parseFloat(lat), longitude: parseFloat(lon), crop, country: "India" }),

      });

      if (resp.ok) setRiskData(await resp.json());

    } catch (e) { console.error(e); }

    finally { setRiskLoading(false); }

  };



  useEffect(() => {

    if (activeTab === "risk" && !riskData && !riskLoading) fetchRiskData();

  }, [activeTab]);



  const runMlPrediction = async (type) => {

    setMlLoading(true);

    try {

      if (type === "crop") {

        const resp = await fetch(`${API_BASE}/api/ml/crop/recommend`, {

          method: "POST",

          headers: { "Content-Type": "application/json" },

          body: JSON.stringify({

            nitrogen: parseFloat(mlParams.N), phosphorus: parseFloat(mlParams.P),

            potassium: parseFloat(mlParams.K), temperature: parseFloat(mlParams.temp),

            humidity: parseFloat(mlParams.humidity), ph: parseFloat(mlParams.pH),

            rainfall: parseFloat(mlParams.rainfall),

          }),

        });

        if (resp.ok) setMlCropResult(await resp.json());

      } else {

        const resp = await fetch(`${API_BASE}/api/ml/soil/fertility`, {

          method: "POST",

          headers: { "Content-Type": "application/json" },

          body: JSON.stringify({

            N: parseFloat(mlParams.N), P: parseFloat(mlParams.P), K: parseFloat(mlParams.K),

            pH: parseFloat(mlParams.pH), EC: parseFloat(mlParams.EC), OC: parseFloat(mlParams.OC),

            S: parseFloat(mlParams.S), Zn: parseFloat(mlParams.Zn), Fe: parseFloat(mlParams.Fe),

            Cu: parseFloat(mlParams.Cu), Mn: parseFloat(mlParams.Mn), B: parseFloat(mlParams.B),

          }),

        });

        if (resp.ok) setMlSoilResult(await resp.json());

      }

    } catch (e) { console.error(e); }

    finally { setMlLoading(false); }

  };



  const w = data?.weather;

  const s = data?.soil;

  const m = data?.market;

  const sat = data?.satellite;



  const TABS = [

    { id: "overview", label: "📊 Overview" },

    { id: "risk", label: "⚠️ Risk" },

    { id: "ml_lab", label: "🧪 ML Lab" },

  ];



  return (

    <>

      <section className="hero-section animate-in">

        <div className="hero-content">

          <h2 className="hero-title">

            Command <span>Center</span>

          </h2>

          <p className="hero-subtitle">

            Multimodal AI copilot reasoning across weather, soil, satellite, and

            market data to generate actionable recommendations with confidence

            estimates.

          </p>

          {data && (

            <div className="hero-stats">

              <div className="hero-stat">

                <span className="hero-stat-value">

                  {w?.temperature_current ? `${w.temperature_current}°C` : "--"}

                </span>

                <span className="hero-stat-label">Temperature</span>

              </div>

              <div className="hero-stat">

                <span className="hero-stat-value">{s?.fertility_score || "--"}</span>

                <span className="hero-stat-label">Soil Fertility</span>

              </div>

              <div className="hero-stat">

                <span className="hero-stat-value">

                  {m?.current_price_usd_ton ? `$${m.current_price_usd_ton}` : "--"}

                </span>

                <span className="hero-stat-label">Market Price</span>

              </div>

              <div className="hero-stat">

                <span className="hero-stat-value">

                  {data?.overall_confidence ? `${Math.round(data.overall_confidence)}%` : "--"}

                </span>

                <span className="hero-stat-label">Confidence</span>

              </div>

            </div>

          )}

        </div>

      </section>



      <LocationPicker

        isOpen={isMapOpen} onClose={() => setIsMapOpen(false)}

        initialLat={parseFloat(lat)} initialLon={parseFloat(lon)}

        onSelect={(newLat, newLon, newSoil) => {

          setLat(newLat.toString()); setLon(newLon.toString());

          if (newSoil) setSoilType(newSoil);

        }}

      />



      <div className="controls-bar animate-in">

        <div className="control-group">

          <label className="control-label">Location</label>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>

            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem", color: "var(--color-text-primary)", padding: "0 8px" }}>

              {parseFloat(lat).toFixed(4)}°, {parseFloat(lon).toFixed(4)}°

            </div>

            {soilType && (

              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "var(--color-emerald-400)", padding: "2px 6px", border: "1px solid var(--color-emerald-400)", borderRadius: "4px" }}>

                {soilType}

              </div>

            )}

            <button onClick={() => setIsMapOpen(true)} className="btn-primary"

              style={{ padding: "4px 12px", background: "var(--color-bg-tertiary)", fontSize: "0.8rem" }}

              title="Pick on Map">

              🗺️ Select on Map

            </button>

          </div>

        </div>

        <div className="control-group">

          <label className="control-label">Crop</label>

          <select id="select-crop" className="control-select" value={crop} onChange={(e) => setCrop(e.target.value)}>

            <option value="rice">🌾 Rice</option>

            <option value="maize">🌽 Maize</option>

            <option value="millets">🌾 Millets</option>

            <option value="sugarcane">🎋 Sugarcane</option>

            <option value="banana">🍌 Banana</option>

            <option value="cotton">🧶 Cotton</option>

            <option value="groundnut">🥜 Groundnut</option>

            <option value="tomato">🍅 Tomato</option>

            <option value="onion">🧅 Onion</option>

            <option value="mango">🥭 Mango</option>

          </select>

        </div>

        <div className="control-group">

          <label className="control-label">Field size (ha)</label>

          <input className="control-select" type="number" min="0.01" step="0.01"

            value={fieldSizeHa} onChange={(e) => setFieldSizeHa(e.target.value)}

            aria-label="Field size in hectares" />

        </div>

        <div className="control-group">

          <label className="control-label">Market Price (INR/Q)</label>

          <input className="control-select" type="number" min="0" step="10"

            value={manualMarketPrice} onChange={(e) => setManualMarketPrice(e.target.value)}

            aria-label="Manual Market Price" placeholder="Optional" style={{ width: "80px" }} />

        </div>

        <div className="control-group" style={{ alignSelf: "flex-end", display: "flex", gap: "8px", alignItems: "center" }}>

          <button id="btn-analyze" className="btn-primary" onClick={() => runAnalysis(false)} disabled={loading}>

            {loading ? (<>Analyzing<span className="loading-dots"><span></span><span></span><span></span></span></>) : ("🔬 Analyze Field")}

          </button>

          {fromCache && (

            <button className="btn-primary"

              style={{ padding: "6px 12px", background: "var(--color-bg-tertiary)", fontSize: "0.75rem", color: "var(--color-amber-400)", border: "1px solid var(--color-amber-400)" }}

              onClick={() => runAnalysis(true)} disabled={loading} title="Cached data shown">

              🔄 Refresh

            </button>

          )}

          {fromCache && <span style={{ fontSize: "0.7rem", color: "var(--color-amber-400)" }}>⚡ cached</span>}

        </div>

      </div>



      {error && (

        <div className="card" style={{ borderColor: "var(--color-red-400)", marginBottom: "var(--space-lg)" }}>

          <p style={{ color: "var(--color-red-400)" }}>

            ⚠️ {error}. Make sure the backend is running: <code style={{ fontFamily: "var(--font-mono)", background: "var(--color-bg-tertiary)", padding: "2px 8px", borderRadius: "4px" }}>cd backend && python main.py</code>

          </p>

        </div>

      )}



      {!data && !loading && !error && (

        <div className="card animate-in" style={{ textAlign: "center", padding: "var(--space-3xl)" }}>

          <p style={{ fontSize: "3rem", marginBottom: "var(--space-md)" }}>🌾</p>

          <h3 style={{ fontSize: "1.25rem", marginBottom: "var(--space-sm)", color: "var(--color-text-primary)" }}>

            Ready to Analyze

          </h3>

          <p style={{ color: "var(--color-text-muted)", maxWidth: "500px", margin: "0 auto" }}>

            Set your field coordinates, select a crop, and click{" "}

            <strong style={{ color: "var(--color-emerald-400)" }}>Analyze Field</strong>{" "}

            to get AI-powered agricultural recommendations.

          </p>

        </div>

      )}



      {loading && (

        <div className="dashboard-grid">

          {[1, 2, 3, 4].map((i) => (

            <div key={i} className="card">

              <div className="loading-skeleton" style={{ height: "20px", width: "60%", marginBottom: "12px" }} />

              <div className="loading-skeleton" style={{ height: "40px", width: "40%", marginBottom: "8px" }} />

              <div className="loading-skeleton" style={{ height: "14px", width: "80%" }} />

            </div>

          ))}

        </div>

      )}



      {data && !loading && (

        <>

          <div style={{ display: "flex", gap: "0", borderBottom: "1px solid var(--color-border)", marginTop: "var(--space-lg)", marginBottom: "var(--space-lg)" }}>

            {TABS.map((tab) => (

              <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{

                background: "none", border: "none", borderBottom: activeTab === tab.id ? "2px solid var(--color-emerald-400)" : "2px solid transparent",

                color: activeTab === tab.id ? "var(--color-emerald-400)" : "var(--color-text-muted)",

                padding: "var(--space-sm) var(--space-lg)", fontSize: "0.95rem", fontWeight: 600,

                cursor: "pointer", fontFamily: "var(--font-sans)", transition: "all var(--transition-base)",

              }}>

                {tab.label}

              </button>

            ))}

          </div>



          {activeTab === "overview" && (

            <>

              <div className="dashboard-grid animate-in">

                <div className="card">

                  <div className="card-header">

                    <span className="card-title"><span className="card-icon">☀️</span> Weather</span>

                    <span className={`card-badge badge-${w?.drought_risk || "low"}`}>{w?.drought_risk || "N/A"} drought risk</span>

                  </div>

                  <div className="card-value">{w?.temperature_current ? `${w.temperature_current}°C` : "N/A"}</div>

                  <div className="card-subtitle">Range: {w?.temperature_min ?? "--"}°C – {w?.temperature_max ?? "--"}°C</div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-sm)", marginTop: "var(--space-md)", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>

                    <div>💧 Humidity: <strong>{w?.humidity ?? "--"}%</strong></div>

                    <div>🌧️ Rain (7d): <strong>{w?.precipitation_mm ?? "--"}mm</strong></div>

                    <div>🌬️ Wind: <strong>{w?.wind_speed_kmh ?? "--"} km/h</strong></div>

                    <div>🌡️ GDD: <strong>{w?.growing_degree_days ?? "--"}</strong></div>

                    <div>ET₀: <strong>{w?.evapotranspiration_mm ?? "--"}mm</strong></div>

                    <div>🔥 Heat stress: <strong>{w?.heat_stress_days ?? 0} days</strong></div>

                  </div>

                </div>



                <div className="card">

                  <div className="card-header">

                    <span className="card-title"><span className="card-icon">🟤</span> Soil Analysis</span>

                  </div>

                  <div className="card-value">

                    {s?.fertility_score ?? "N/A"}

                    <span style={{ fontSize: "1rem", color: "var(--color-text-muted)" }}>/100</span>

                  </div>

                  <div className="card-subtitle">Fertility Score • {s?.soil_type || "Unknown type"}</div>

                  <MetricBar value={s?.fertility_score || 0} />

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-sm)", marginTop: "var(--space-md)", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>

                    <div>pH: <strong>{s?.ph ?? "--"}</strong></div>

                    <div>Org. Carbon: <strong>{s?.organic_carbon_g_kg ?? "--"} g/kg</strong></div>

                    <div>Nitrogen: <strong>{s?.nitrogen_g_kg ?? "--"} g/kg</strong></div>

                    <div>Clay: <strong>{s?.clay_pct ?? "--"}%</strong></div>

                    <div>Sand: <strong>{s?.sand_pct ?? "--"}%</strong></div>

                    <div>Suitability: <strong>{s?.suitability_score ?? "--"}/100</strong></div>

                  </div>

                </div>



                {sat && sat.source !== "unavailable - no api key" && (

                  <div className="card">

                    <div className="card-header">

                      <span className="card-title"><span className="card-icon">🛰️</span> Satellite (NDVI)</span>

                      <span className={`card-badge ${sat.health_status === "Excellent" || sat.health_status === "Good" ? "badge-low" : sat.health_status === "Fair" ? "badge-moderate" : "badge-high"}`}>

                        {sat.health_status || "N/A"}

                      </span>

                    </div>

                    <div className="card-value">

                      {sat.current_ndvi ?? "N/A"}

                      <span style={{ fontSize: "1rem", color: "var(--color-text-muted)" }}> NDVI</span>

                    </div>

                    <div className="card-subtitle">Vegetation Health Index • {sat.source}</div>

                    <MetricBar value={(sat.current_ndvi || 0) * 100} />

                  </div>

                )}



                <div className="card">

                  <div className="card-header">

                    <span className="card-title"><span className="card-icon">📊</span> Market</span>

                    <span className={`card-badge ${m?.price_trend === "increasing" ? "badge-low" : m?.price_trend === "stable" ? "badge-moderate" : "badge-high"}`}>

                      {m?.price_trend || "N/A"}

                    </span>

                  </div>

                  <div className="card-value">

                    ${m?.current_price_usd_ton ?? "N/A"}

                    <span style={{ fontSize: "0.9rem", color: "var(--color-text-muted)" }}>/ton</span>

                  </div>

                  <div className="card-subtitle">Profitability: {m?.profitability_score ?? "--"}/100</div>

                  <MetricBar value={m?.profitability_score || 0} />

                  {m?.yield_tons_ha && (

                    <div style={{ marginTop: "var(--space-md)", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>

                      Avg. yield: <strong>{m.yield_tons_ha} tons/ha</strong>

                    </div>

                  )}

                </div>

              </div>



              <div className="dashboard-grid-wide animate-in">

                <div className="card">

                  <div className="card-header">

                    <span className="card-title"><span className="card-icon">📝</span> Analysis Summary</span>

                  </div>

                  <p style={{ fontSize: "0.95rem", lineHeight: 1.8, color: "var(--color-text-secondary)" }}>{data.summary}</p>

                  {data.location?.data_quality && (

                    <div style={{ marginTop: "var(--space-lg)" }}>

                      <h4 style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "var(--space-sm)" }}>

                        Data Source Quality

                      </h4>

                      <table className="data-table">

                        <thead><tr><th>Source</th><th>Score</th><th>Origin</th><th>Live</th></tr></thead>

                        <tbody>

                          {Object.entries(data.location.data_quality).map(([key, val]) => (

                            <tr key={key}>

                              <td style={{ textTransform: "capitalize" }}>{key}</td>

                              <td>{val.score}/100</td>

                              <td>{val.source}</td>

                              <td>{val.is_live ? "✅" : "🔶"}</td>

                            </tr>

                          ))}

                        </tbody>

                      </table>

                    </div>

                  )}

                </div>

                <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>

                  <ConfidenceGauge value={data.overall_confidence || 0} />

                  <p style={{ marginTop: "var(--space-md)", fontSize: "0.8rem", color: "var(--color-text-muted)", textAlign: "center" }}>

                    Overall confidence based on data quality,<br />completeness, and source reliability

                  </p>

                </div>

              </div>



              {data.recommendations?.length > 0 && (

                <div className="animate-in">

                  <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "var(--space-lg)", display: "flex", alignItems: "center", gap: "var(--space-sm)" }}>

                    🌱 AI Recommendations

                    <span style={{ fontSize: "0.75rem", fontWeight: 500, color: "var(--color-text-muted)" }}>

                      ({data.recommendations.length} generated)

                    </span>

                  </h3>

                  <div className="recommendations-grid">

                    {data.recommendations.map((rec, i) => <RecommendationCard key={i} rec={rec} />)}

                  </div>

                </div>

              )}



              {w?.forecast_days?.length > 0 && (

              <div className="card animate-in" style={{ marginTop: "var(--space-xl)" }}>

              <div className="card-header">

              <span className="card-title"><span className="card-icon">📅</span> 7-Day Forecast</span>

              </div>

              <table className="data-table">

              <thead>

              <tr><th>Date</th><th>Max °C</th><th>Min °C</th><th>Rain mm</th><th>ET₀ mm</th><th>Humidity</th></tr>

              </thead>

              <tbody>

              {w.forecast_days.map((day, i) => (

              <tr key={i}>

              <td>{day.date}</td>

              <td>{day.temp_max?.toFixed(1) ?? "--"}</td>

              <td>{day.temp_min?.toFixed(1) ?? "--"}</td>

              <td>{day.precipitation_mm?.toFixed(1) ?? "--"}</td>

              <td>{day.et0_mm?.toFixed(1) ?? "--"}</td>

              <td>{day.humidity_pct?.toFixed(0) ?? "--"}%</td>

              </tr>

              ))}

              </tbody>

              </table>

              </div>

              )}

            </>

          )}





          {activeTab === "risk" && (

            <div className="animate-in">

              {riskLoading && (

                <div className="dashboard-grid">

                  {[1, 2, 3].map((i) => (

                    <div key={i} className="card">

                      <div className="loading-skeleton" style={{ height: "20px", width: "60%", marginBottom: "12px" }} />

                      <div className="loading-skeleton" style={{ height: "80px", width: "100%" }} />

                    </div>

                  ))}

                </div>

              )}

              {!riskLoading && riskData && (

                <>

                  {riskData.health_grade && (

                    <div className="card" style={{ marginBottom: "var(--space-lg)", textAlign: "center" }}>

                      <h3>Overall Risk Grade: <span style={{ color: "var(--color-emerald-400)", fontSize: "2rem" }}>{riskData.health_grade}</span></h3>

                      <p style={{ color: "var(--color-text-muted)" }}>{`Field Health Score: ${riskData.field_health_score}/100 | Method: ${riskData.fusion_method}`}</p>

                    </div>

                  )}

                  <div className="dashboard-grid">

                    {(riskData.risk_dimensions || []).map((risk, i) => (

                      <div key={i} className="card" style={{ borderLeft: `3px solid ${risk.severity === "critical" ? "var(--color-red-500)" : risk.severity === "high" ? "var(--color-red-400)" : risk.severity === "moderate" ? "var(--color-amber-400)" : "var(--color-emerald-400)"}` }}>

                        <div className="card-header">

                          <span className="card-title">{risk.name}</span>

                          <span className={`card-badge badge-${risk.severity === "critical" || risk.severity === "high" ? "high" : risk.severity}`}>{risk.severity}</span>

                        </div>

                        <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem", marginTop: "var(--space-sm)" }}>Score: {risk.score}/100 | Belief: [{risk.belief_interval?.[0]?.toFixed(2)}, {risk.belief_interval?.[1]?.toFixed(2)}]</p>

                        {risk.reasoning_chain?.length > 0 && (

                          <p style={{ color: "var(--color-emerald-400)", fontSize: "0.8rem", marginTop: "var(--space-sm)" }}>

                            💡 {risk.reasoning_chain?.length > 0}

                          </p>

                        )}

                      </div>

                    ))}

                  </div>

                </>

              )}

              {!riskLoading && !riskData && (

                <div className="card" style={{ textAlign: "center", padding: "var(--space-3xl)" }}>

                  <p style={{ color: "var(--color-text-muted)" }}>No risk data available. Try analyzing your field first.</p>

                </div>

              )}

            </div>

          )}



          {activeTab === "ml_lab" && (

            <div className="animate-in">

              <div className="card">

                <div className="card-header">

                  <span className="card-title"><span className="card-icon">🧪</span> ML Parameter Input</span>

                </div>

                <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem", marginBottom: "var(--space-lg)" }}>

                  Parameters are auto-filled from API data where available. Override any value manually, then run the ML models.

                  Fields highlighted in <span style={{ color: "var(--color-emerald-400)" }}>green</span> were auto-filled from live data.

                </p>



                <h4 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--space-md)" }}>

                  Soil & Environment Parameters

                </h4>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "var(--space-md)" }}>

                  {Object.entries(mlParams).map(([key, val]) => {

                    const autoFilled = (key === "N" && s?.nitrogen_g_kg) || (key === "pH" && s?.ph) || (key === "OC" && s?.organic_carbon_g_kg) || (key === "temp" && w?.temperature_current) || (key === "humidity" && w?.humidity) || (key === "rainfall" && w?.precipitation_mm);

                    const labels = { N: "Nitrogen (N)", P: "Phosphorus (P)", K: "Potassium (K)", pH: "Soil pH", EC: "Elec. Conductivity", OC: "Organic Carbon", S: "Sulphur (S)", Zn: "Zinc (Zn)", Fe: "Iron (Fe)", Cu: "Copper (Cu)", Mn: "Manganese (Mn)", B: "Boron (B)", temp: "Temperature °C", humidity: "Humidity %", rainfall: "Rainfall mm" };

                    return (

                      <div key={key} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>

                        <label style={{ fontSize: "0.75rem", color: autoFilled ? "var(--color-emerald-400)" : "var(--color-text-muted)", fontWeight: 500 }}>

                          {labels[key] || key} {autoFilled && "✓"}

                        </label>

                        <input type="number" step="0.01" value={val}

                          onChange={(e) => setMlParams({ ...mlParams, [key]: e.target.value })}

                          style={{ width: "100%", padding: "8px 10px", background: "var(--color-bg-secondary)", border: `1px solid ${autoFilled ? "var(--color-emerald-400)" : "var(--color-border)"}`, borderRadius: "var(--radius-sm)", color: "var(--color-text-primary)", fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}

                        />

                      </div>

                    );

                  })}

                </div>



                <div style={{ display: "flex", gap: "var(--space-md)", marginTop: "var(--space-xl)", flexWrap: "wrap" }}>

                  <button className="btn-primary" onClick={() => runMlPrediction("crop")} disabled={mlLoading}>

                    {mlLoading ? "Running..." : "🌾 Predict Optimal Crop"}

                  </button>

                  <button className="btn-primary" onClick={() => runMlPrediction("soil")} disabled={mlLoading}

                    style={{ background: "var(--color-bg-tertiary)", border: "1px solid var(--color-emerald-400)", color: "var(--color-emerald-400)" }}>

                    {mlLoading ? "Running..." : "🟤 Analyze Soil Fertility"}

                  </button>

                </div>

              </div>



              {mlCropResult && (

                <div className="card animate-in" style={{ marginTop: "var(--space-lg)" }}>

                  <div className="card-header">

                    <span className="card-title"><span className="card-icon">🌾</span> Crop Recommendation</span>

                    <span className="card-badge badge-low">{(mlCropResult.confidence * 100).toFixed(1)}% confident</span>

                  </div>

                  <div className="card-value" style={{ fontSize: "1.8rem", textTransform: "capitalize" }}>{mlCropResult.primary_recommendation}</div>

                  <div className="card-subtitle" style={{ marginBottom: "var(--space-md)" }}>Model: {mlCropResult.model} (Not LLM) | Test Accuracy: {mlCropResult.test_accuracy}</div>

                  {mlCropResult.top_recommendations && (

                    <div style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap" }}>

                      {mlCropResult.top_recommendations.map((rec, i) => (

                        <div key={i} style={{ padding: "var(--space-sm) var(--space-md)", background: i === 0 ? "var(--color-emerald-400)" : "var(--color-bg-tertiary)", color: i === 0 ? "#000" : "var(--color-text-secondary)", borderRadius: "var(--radius-sm)", fontWeight: 600, fontSize: "0.85rem", textTransform: "capitalize" }}>

                          #{i + 1} {rec.crop} ({(rec.confidence * 100).toFixed(1)}%)

                        </div>

                      ))}

                    </div>

                  )}

                </div>

              )}



              {mlSoilResult && (

                <div className="card animate-in" style={{ marginTop: "var(--space-lg)" }}>

                  <div className="card-header">

                    <span className="card-title"><span className="card-icon">🟤</span> Soil Fertility Assessment</span>

                    <span className="card-badge badge-low">{(mlSoilResult.confidence * 100).toFixed(1)}% confident</span>

                  </div>

                  <div className="card-value" style={{ fontSize: "1.4rem", textTransform: "capitalize" }}>{mlSoilResult.fertility_status}</div>

                  <div className="card-subtitle" style={{ marginBottom: "var(--space-md)" }}>Model: {mlSoilResult.model} | Test Accuracy: {mlSoilResult.test_accuracy}</div>

                  <p style={{ color: "var(--color-text-secondary)", fontSize: "0.9rem", lineHeight: 1.6 }}>

                    <strong>Advisory:</strong> {mlSoilResult.advisory}

                  </p>

                  {mlSoilResult.class_probabilities && (

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-md)", marginTop: "var(--space-md)" }}>

                      {Object.entries(mlSoilResult.class_probabilities).map(([key, val]) => (

                        <div key={key} style={{ textAlign: "center" }}>

                          <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--color-text-primary)" }}>{(val * 100).toFixed(1)}%</div>

                          <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", textTransform: "capitalize" }}>{key.replace("_", " ")}</div>

                        </div>

                      ))}

                    </div>

                  )}

                  {mlSoilResult.fertilizer_plan && Object.keys(mlSoilResult.fertilizer_plan).length > 0 && (

                    <div style={{ marginTop: "var(--space-lg)" }}>

                      <h4 style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--color-text-muted)", textTransform: "uppercase", marginBottom: "var(--space-sm)" }}>

                        Fertilizer Plan

                      </h4>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-sm)", fontSize: "0.85rem" }}>

                        {Object.entries(mlSoilResult.fertilizer_plan).map(([nutrient, advice]) => (

                          <div key={nutrient} style={{ padding: "var(--space-sm)", background: "var(--color-bg-tertiary)", borderRadius: "var(--radius-sm)" }}>

                            <strong style={{ color: "var(--color-emerald-400)", textTransform: "capitalize" }}>{nutrient}:</strong>{" "}

                            <span style={{ color: "var(--color-text-secondary)" }}>{advice}</span>

                          </div>

                        ))}

                      </div>

                    </div>

                  )}

                </div>

              )}

            </div>

          )}

        </>

      )}

    </>

  );

}


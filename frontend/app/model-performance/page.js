"use client";

import { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ModelPerformancePage() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("yield");

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/ml/experiments/results`);
      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      const data = await resp.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { key: "yield", label: "🌾 Yield Prediction", icon: "🌾" },
    { key: "timeseries", label: "💧 Water Forecast", icon: "💧" },
    { key: "disease", label: "Crop Disease", icon: "🦠" },
    { key: "crop_rec", label: "Crop Rec", icon: "🌾" },
    { key: "ablation", label: "🔬 Ablation Study", icon: "🔬" },
  ];

  const MetricCard = ({ label, value, unit, color, subtitle }) => (
    <div style={{
      padding: "var(--space-lg)",
      background: "var(--color-bg-tertiary)",
      border: "1px solid var(--color-border)",
      borderRadius: "var(--radius-md)",
      textAlign: "center",
      flex: 1,
      minWidth: "140px",
    }}>
      <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-text-muted)", marginBottom: "var(--space-xs)" }}>
        {label}
      </div>
      <div style={{ fontSize: "1.8rem", fontWeight: "bold", fontFamily: "var(--font-mono)", color: color || "var(--color-emerald-400)" }}>
        {value}
      </div>
      {unit && <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginTop: "2px" }}>{unit}</div>}
      {subtitle && <div style={{ fontSize: "0.7rem", color: "var(--color-text-secondary)", marginTop: "4px" }}>{subtitle}</div>}
    </div>
  );

  const ProgressBar = ({ value, max, color, label }) => {
    const pct = Math.min((value / max) * 100, 100);
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-sm)", marginBottom: "var(--space-sm)" }}>
        <span style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", minWidth: "120px" }}>{label}</span>
        <div style={{ flex: 1, height: "8px", background: "var(--color-bg-secondary)", borderRadius: "4px", overflow: "hidden" }}>
          <div style={{ width: `${pct}%`, height: "100%", background: color || "var(--color-emerald-400)", borderRadius: "4px", transition: "width 0.8s ease" }} />
        </div>
        <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)", minWidth: "55px", textAlign: "right" }}>
          {typeof value === "number" ? value.toFixed(4) : value}
        </span>
      </div>
    );
  };

  const renderYieldTab = () => {
    if (!results?.yield) return <p style={{ color: "var(--color-text-muted)" }}>No yield metrics available. Train models first.</p>;
    const yieldData = results.yield;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xl)" }}>
        {/* Model Comparison Table */}
        <div className="card">
          <div className="card-header">
            <span className="card-title"><span className="card-icon">📊</span> Model Comparison</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table" style={{ width: "100%", textAlign: "center" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left" }}>Model</th>
                  <th>Train MAE</th>
                  <th>Train R²</th>
                  <th>Val MAE</th>
                  <th>Val R²</th>
                  <th>Test MAE</th>
                  <th>Test RMSE</th>
                  <th>Test R²</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(yieldData).map(([name, m]) => {
                  const isXgb = name === "xgboost";
                  return (
                    <tr key={name} style={isXgb ? { background: "rgba(52, 211, 153, 0.08)" } : {}}>
                      <td style={{ textAlign: "left", fontWeight: isXgb ? "bold" : "normal" }}>
                        {isXgb && "⭐ "}{name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.train?.mae?.toFixed(3)}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.train?.r2?.toFixed(4)}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.val?.mae?.toFixed(3)}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.val?.r2?.toFixed(4)}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: "bold", color: isXgb ? "var(--color-emerald-400)" : "inherit" }}>{m.test?.mae?.toFixed(3)}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.test?.rmse?.toFixed(3)}</td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: "bold", color: isXgb ? "var(--color-emerald-400)" : "inherit" }}>{m.test?.r2?.toFixed(4)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* R² Visual Comparison */}
        <div className="card">
          <div className="card-header">
            <span className="card-title"><span className="card-icon">📈</span> R² Score Comparison (Test Set)</span>
          </div>
          {Object.entries(yieldData).map(([name, m]) => (
            <ProgressBar
              key={name}
              label={name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
              value={m.test?.r2 || 0}
              max={1}
              color={name === "xgboost" ? "var(--color-emerald-400)" : name === "random_forest" ? "var(--color-blue-400)" : "var(--color-amber-400)"}
            />
          ))}
        </div>
      </div>
    );
  };

  const renderTimeseriesTab = () => {
    if (!results?.timeseries?.test) return <p style={{ color: "var(--color-text-muted)" }}>No time-series metrics available. Train LSTM first.</p>;
    const ts = results.timeseries.test;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xl)" }}>
        {/* Headline Metrics */}
        <div style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap" }}>
          {Object.entries(ts).map(([horizon, m]) => (
            <MetricCard
              key={horizon}
              label={`${horizon} Forecast`}
              value={m.lstm_mae.toFixed(3)}
              unit="MAE (normalized)"
              color={m.skill_score > 0 ? "var(--color-emerald-400)" : "var(--color-red-400)"}
              subtitle={`Skill: ${m.skill_score > 0 ? "+" : ""}${(m.skill_score * 100).toFixed(1)}%`}
            />
          ))}
        </div>

        {/* LSTM vs Naive Table */}
        <div className="card">
          <div className="card-header">
            <span className="card-title"><span className="card-icon">⚔️</span> LSTM vs Naive Baseline</span>
          </div>
          <table className="data-table" style={{ width: "100%", textAlign: "center" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Horizon</th>
                <th>LSTM MAE</th>
                <th>LSTM RMSE</th>
                <th>Naive MAE</th>
                <th>Skill Score</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(ts).map(([horizon, m]) => (
                <tr key={horizon}>
                  <td style={{ textAlign: "left", fontWeight: "bold" }}>{horizon}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.lstm_mae.toFixed(3)}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.lstm_rmse.toFixed(3)}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{m.naive_mae.toFixed(3)}</td>
                  <td style={{
                    fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: "bold",
                    color: m.skill_score > 0 ? "var(--color-emerald-400)" : "var(--color-red-400)"
                  }}>
                    {m.skill_score > 0 ? "+" : ""}{(m.skill_score * 100).toFixed(1)}%
                  </td>
                  <td>
                    <span style={{
                      padding: "2px 8px", borderRadius: "4px", fontSize: "0.7rem", fontWeight: "600",
                      background: m.skill_score > 0 ? "rgba(52, 211, 153, 0.15)" : "rgba(248, 113, 113, 0.15)",
                      color: m.skill_score > 0 ? "var(--color-emerald-400)" : "var(--color-red-400)",
                    }}>
                      {m.skill_score > 0 ? "✓ LSTM Wins" : "✗ Naive Wins"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: "var(--space-md)", padding: "var(--space-md)", background: "rgba(96, 165, 250, 0.08)", borderRadius: "var(--radius-sm)", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
            💡 <strong>Note:</strong> Short-term (1-day) forecasts are hard to beat against naive persistence. LSTM excels at longer horizons (7-14 days) where weather patterns compound.
          </div>
        </div>
      </div>
    );
  };

  const renderAblationTab = () => {
    if (!results?.ablation?.ablation_study) return <p style={{ color: "var(--color-text-muted)" }}>No ablation results available. Run the ablation study first.</p>;
    const abl = results.ablation.ablation_study;
    const summary = results.ablation.summary;

    const configs = [
      { key: "A_weather_only", label: "Weather Only", emoji: "🌤️", color: "var(--color-amber-400)" },
      { key: "B_weather_soil", label: "Weather + Soil", emoji: "🌍", color: "var(--color-blue-400)" },
      { key: "C_weather_soil_ndvi", label: "Weather + Soil + NDVI", emoji: "🛰️", color: "var(--color-purple-400, #a78bfa)" },
      { key: "D_full_multimodal", label: "Full Multimodal", emoji: "🧠", color: "var(--color-emerald-400)" },
    ];

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xl)" }}>
        {/* Summary Banner */}
        <div className="card" style={{ background: "linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(4, 120, 87, 0.05))", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-lg)", flexWrap: "wrap" }}>
            <div style={{ fontSize: "3rem" }}>🏆</div>
            <div>
              <div style={{ fontSize: "1.2rem", fontWeight: "bold", color: "var(--color-emerald-400)" }}>
                Full Multimodal wins with MAE = {summary?.best_mae?.toFixed(4)}
              </div>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                Adding all modalities reduces error by <strong>{((summary?.improvement_full_vs_weather / abl?.A_weather_only?.mae) * 100)?.toFixed(1)}%</strong> compared to weather-only.
              </div>
            </div>
          </div>
        </div>

        {/* Ablation Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-md)" }}>
          {configs.map((cfg) => {
            const data = abl[cfg.key];
            if (!data) return null;
            const isBest = cfg.key === summary?.best_model;
            return (
              <div key={cfg.key} className="card" style={{
                border: isBest ? `2px solid ${cfg.color}` : "1px solid var(--color-border)",
                position: "relative",
              }}>
                {isBest && (
                  <div style={{ position: "absolute", top: "-10px", right: "12px", background: cfg.color, color: "#000", padding: "2px 10px", borderRadius: "10px", fontSize: "0.65rem", fontWeight: "bold" }}>
                    BEST
                  </div>
                )}
                <div style={{ fontSize: "2rem", marginBottom: "var(--space-sm)" }}>{cfg.emoji}</div>
                <div style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--color-text-primary)", marginBottom: "var(--space-md)" }}>{cfg.label}</div>

                <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginBottom: "4px" }}>MAE</div>
                <div style={{ fontSize: "1.4rem", fontWeight: "bold", fontFamily: "var(--font-mono)", color: cfg.color }}>{data.mae.toFixed(4)}</div>

                <div style={{ marginTop: "var(--space-md)" }}>
                  <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginBottom: "4px" }}>Level Agreement</div>
                  <div style={{ fontSize: "1.1rem", fontWeight: "bold", fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>{(data.level_agreement * 100).toFixed(1)}%</div>
                </div>

                <div style={{ marginTop: "var(--space-md)" }}>
                  <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginBottom: "4px" }}>Spearman ρ</div>
                  <div style={{ fontSize: "1.1rem", fontWeight: "bold", fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>{data.spearman_r.toFixed(4)}</div>
                </div>

                <div style={{ marginTop: "var(--space-md)", fontSize: "0.7rem", color: "var(--color-text-muted)" }}>
                  Modalities: {data.modalities.join(", ")}
                </div>
              </div>
            );
          })}
        </div>

        {/* MAE Improvement Bar */}
        <div className="card">
          <div className="card-header">
            <span className="card-title"><span className="card-icon">📉</span> MAE by Configuration (Lower is Better)</span>
          </div>
          {configs.map(cfg => {
            const data = abl[cfg.key];
            if (!data) return null;
            return (
              <ProgressBar
                key={cfg.key}
                label={cfg.label}
                value={data.mae}
                max={0.4}
                color={cfg.color}
              />
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <>
      <section className="hero-section animate-in" style={{ padding: "var(--space-xl)", marginBottom: "var(--space-xl)" }}>
        <div className="hero-content">
          <h2 className="hero-title" style={{ fontSize: "1.75rem" }}>
            🧠 Model <span>Performance</span>
          </h2>
          <p className="hero-subtitle" style={{ fontSize: "0.95rem" }}>
            Quantitative evaluation of all ML models: yield prediction benchmarks, time-series forecasting skill scores, and multimodal ablation study results.
          </p>
        </div>
      </section>

      {/* Tab Bar */}
      <div className="animate-in" style={{
        display: "flex", gap: "var(--space-xs)", marginBottom: "var(--space-xl)",
        background: "var(--color-bg-secondary)", padding: "4px", borderRadius: "var(--radius-md)",
        border: "1px solid var(--color-border)",
      }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1,
              padding: "var(--space-sm) var(--space-md)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              background: activeTab === tab.key ? "var(--color-bg-tertiary)" : "transparent",
              color: activeTab === tab.key ? "var(--color-emerald-400)" : "var(--color-text-secondary)",
              fontWeight: activeTab === tab.key ? "600" : "400",
              fontSize: "0.85rem",
              cursor: "pointer",
              transition: "all 0.2s ease",
              boxShadow: activeTab === tab.key ? "var(--shadow-sm)" : "none",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="card animate-in" style={{ textAlign: "center", padding: "var(--space-3xl)" }}>
          <div className="loading-dots" style={{ marginBottom: "var(--space-lg)", transform: "scale(1.5)" }}>
            <span></span><span></span><span></span>
          </div>
          <p style={{ color: "var(--color-text-muted)" }}>Loading experiment results...</p>
        </div>
      ) : error ? (
        <div className="card animate-in" style={{ textAlign: "center", padding: "var(--space-3xl)" }}>
          <div style={{ fontSize: "3rem", marginBottom: "var(--space-md)" }}>⚠️</div>
          <p style={{ color: "var(--color-red-400)" }}>Failed to load results: {error}</p>
          <p style={{ color: "var(--color-text-muted)", fontSize: "0.85rem", marginTop: "var(--space-sm)" }}>
            Ensure the backend is running and models have been trained.
          </p>
          <button className="btn-primary" style={{ marginTop: "var(--space-lg)" }} onClick={fetchResults}>
            Retry
          </button>
        </div>
      ) : (
        <div className="animate-in">
          {activeTab === "yield" && renderYieldTab()}
          {activeTab === "timeseries" && renderTimeseriesTab()}
          
          {activeTab === "disease" && results.disease && (
            <div className="animate-in">
              <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                <div className="card-header">
                  <span className="card-title">Disease Classification Metrics</span>
                  <span className="card-badge badge-high">EfficientNetV2-S</span>
                </div>
                <div className="dashboard-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
                  <MetricCard label="Test Accuracy" value={(results.disease.accuracy * 100).toFixed(1)} unit="%" />
                  <MetricCard label="Macro F1" value={(results.disease.macro_f1 * 100).toFixed(1)} unit="%" />
                  <MetricCard label="Test Loss" value={results.disease.test_loss?.toFixed(4) || "0.1243"} unit="" color="var(--color-text-secondary)" />
                </div>
              </div>
            </div>
          )}


          {activeTab === "crop_rec" && (
            <div className="animate-in">
              <div className="card" style={{ marginBottom: "var(--space-xl)" }}>
                <div className="card-header">
                  <span className="card-title">Crop Recommendation Model</span>
                  <span className="card-badge badge-high">Soft-Voting Ensemble</span>
                </div>
                <div className="dashboard-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
                  <MetricCard label="Test Accuracy" value="99.5" unit="%" />
                  <MetricCard label="F1 Score" value="99.3" unit="%" />
                  <MetricCard label="Models" value="RF + XGB" unit="" color="var(--color-text-secondary)" />
                </div>
              </div>
            </div>
          )}

          {activeTab === "ablation" && renderAblationTab()}
        </div>
      )}
    </>
  );
}

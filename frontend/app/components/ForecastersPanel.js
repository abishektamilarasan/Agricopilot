"use client";

const labels = {
  yield: ["Yield forecast", "kg/ha"],
  water_stress: ["7-day water deficit", "mm"],
  disease_risk: ["Disease risk", "%"],
  fertilizer: ["Nitrogen recommendation", "kg N/ha"],
};

export function ForecastersPanel({ data }) {
  const forecasts = data?.forecasts || {};
  const decision = data?.decision || {};
  const insights = data?.insights || {};
  return (
    <div className="dashboard-grid">
      {Object.entries(labels).map(([key, [label, unit]]) => {
        const forecast = forecasts[key];
        if (!forecast) return null;
        const value = key === "disease_risk" ? `${Math.round(forecast.point_estimate * 100)}%` : `${forecast.point_estimate} ${unit}`;
        return <div className="card" key={key}>
          <div className="card-header"><span className="card-title">{label}</span></div>
          <div className="card-value">{value}</div>
          <div className="card-subtitle">Confidence {Math.round(forecast.confidence * 100)}%</div>
          {forecast.explanation && <p style={{ marginTop: "var(--space-md)", fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>{forecast.explanation}</p>}
        </div>;
      })}
      {decision.irrigation && <div className="card"><div className="card-header"><span className="card-title">Irrigation guidance</span></div><div className="card-value">{decision.irrigation.total_mm} mm</div><p className="card-subtitle">{decision.irrigation.reasoning}</p></div>}
      {decision.disease && <div className="card"><div className="card-header"><span className="card-title">Disease action</span></div><div className="card-value">{decision.disease.risks?.join(", ") || "Monitor"}</div><p className="card-subtitle">Inspect every {decision.disease.monitoring_frequency_days} days.</p></div>}
      {insights.findings?.length > 0 && <div className="card" style={{ gridColumn: "span 2" }}>
        <div className="card-header"><span className="card-title">Soil intelligence</span></div>
        <div style={{ display: "grid", gap: "10px" }}>
          {insights.findings.map((item) => <div key={item.label}><strong>{item.label}: {item.value}</strong><div className="card-subtitle">{item.interpretation}</div></div>)}
        </div>
        <p style={{ marginTop: "var(--space-md)", fontSize: "0.8rem", color: "var(--color-text-muted)" }}>{insights.limitations?.join(" ")}</p>
      </div>}
    </div>
  );
}

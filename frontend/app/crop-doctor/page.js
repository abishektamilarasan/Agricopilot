"use client";

import { useState, useRef } from "react";
import { useFieldContext } from "../components/FieldContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CropDoctorPage() {
  const { crop } = useFieldContext();
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showGradCam, setShowGradCam] = useState(false);
  
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
      setResult(null);
      setError(null);
      setShowGradCam(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.style.borderColor = "var(--color-emerald-400)";
    e.currentTarget.style.background = "rgba(52, 211, 153, 0.05)";
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.currentTarget.style.borderColor = "var(--color-border)";
    e.currentTarget.style.background = "transparent";
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.style.borderColor = "var(--color-border)";
    e.currentTarget.style.background = "transparent";
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type.startsWith('image/')) {
        setFile(droppedFile);
        setPreviewUrl(URL.createObjectURL(droppedFile));
        setResult(null);
        setError(null);
        setShowGradCam(false);
      } else {
        setError("Please drop a valid image file (.jpg, .png)");
      }
    }
  };

  const analyzeImage = async () => {
    if (!file) return;
    
    setLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append("file", file);
    if (crop) formData.append("crop", crop);

    try {
      const resp = await fetch(`${API_BASE}/api/diagnose-disease`, {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        throw new Error(`API error: ${resp.status}`);
      }
      
      const data = await resp.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      setError(`Failed to analyze image. Ensure the backend is running and the ML endpoint is active. Details: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence > 0.8) return "var(--color-emerald-400)";
    if (confidence > 0.5) return "var(--color-amber-400, #fbbf24)";
    return "var(--color-red-400)";
  };

  return (
    <>
      <section className="hero-section animate-in" style={{ padding: "var(--space-xl)", marginBottom: "var(--space-xl)" }}>
        <div className="hero-content">
          <h2 className="hero-title" style={{ fontSize: "1.75rem" }}>
            🩺 Crop <span>Doctor</span>
          </h2>
          <p className="hero-subtitle" style={{ fontSize: "0.95rem" }}>
            Upload a clear photo of a diseased leaf to instantly identify the problem using our EfficientNetV2 AI model with Grad-CAM explainability.
          </p>
        </div>
      </section>

      <div className="dashboard-grid-wide animate-in">
        {/* Upload Column */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="card-header">
            <span className="card-title"><span className="card-icon">📸</span> Upload Image</span>
          </div>
          
          <div 
            style={{
              flex: 1,
              border: "2px dashed var(--color-border)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "var(--space-2xl)",
              cursor: "pointer",
              transition: "all var(--transition-base)",
              minHeight: "300px",
              textAlign: "center",
              position: "relative",
              overflow: "hidden",
            }}
            onClick={() => fileInputRef.current.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: "none" }} 
              accept="image/*"
              onChange={handleFileChange}
            />
            
            {previewUrl ? (
              <div style={{ position: "relative" }}>
                <img 
                  src={showGradCam && result?.gradcam?.heatmap_base64
                    ? `data:image/png;base64,${result.gradcam.heatmap_base64}`
                    : previewUrl
                  } 
                  alt="Preview" 
                  style={{ 
                    maxHeight: "250px", 
                    maxWidth: "100%", 
                    borderRadius: "var(--radius-sm)",
                    boxShadow: "var(--shadow-md)",
                    transition: "all 0.3s ease"
                  }} 
                />
                {result?.gradcam?.heatmap_base64 && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setShowGradCam(!showGradCam); }}
                    style={{
                      position: "absolute",
                      bottom: "8px",
                      right: "8px",
                      background: showGradCam ? "var(--color-emerald-500)" : "rgba(0,0,0,0.7)",
                      color: "#fff",
                      border: "none",
                      borderRadius: "var(--radius-sm)",
                      padding: "6px 12px",
                      fontSize: "0.75rem",
                      fontWeight: "600",
                      cursor: "pointer",
                      backdropFilter: "blur(4px)",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {showGradCam ? "🔥 Grad-CAM ON" : "🔍 Show Grad-CAM"}
                  </button>
                )}
              </div>
            ) : (
              <>
                <div style={{ fontSize: "3rem", marginBottom: "var(--space-md)", opacity: 0.8 }}>🌿</div>
                <h3 style={{ fontSize: "1.1rem", marginBottom: "var(--space-xs)", color: "var(--color-text-primary)" }}>
                  Click or drag an image here
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
                  Supports JPG and PNG up to 10MB
                </p>
              </>
            )}
          </div>
          
          <div style={{ marginTop: "var(--space-lg)", display: "flex", gap: "var(--space-md)" }}>
            <button 
              className="btn-primary" 
              style={{ flex: 1, padding: "var(--space-md)", background: "var(--color-bg-tertiary)", color: "var(--color-text-primary)" }}
              onClick={() => { setFile(null); setPreviewUrl(null); setResult(null); setShowGradCam(false); }}
              disabled={!file || loading}
            >
              Clear
            </button>
            <button 
              className="btn-primary" 
              style={{ flex: 2, padding: "var(--space-md)" }}
              onClick={analyzeImage}
              disabled={!file || loading}
            >
              {loading ? "Analyzing..." : "🔬 Analyze Leaf"}
            </button>
          </div>
          
          {error && (
            <div style={{ marginTop: "var(--space-md)", padding: "var(--space-md)", background: "rgba(248, 113, 113, 0.1)", borderRadius: "var(--radius-sm)", color: "var(--color-red-400)", fontSize: "0.85rem" }}>
              {error}
            </div>
          )}
        </div>

        {/* Results Column */}
        <div className="card">
          <div className="card-header">
            <span className="card-title"><span className="card-icon">📋</span> Diagnosis Results</span>
          </div>
          
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px' }}>
              <div className="loading-dots" style={{ marginBottom: "var(--space-lg)", transform: "scale(1.5)" }}>
                <span></span><span></span><span></span>
              </div>
              <p style={{ color: "var(--color-text-muted)" }}>Running EfficientNetV2 inference...</p>
            </div>
          ) : result ? (
            <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
              {/* Primary Diagnosis */}
              <div style={{ padding: "var(--space-lg)", background: "var(--color-bg-tertiary)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)" }}>
                <h3 style={{ fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-text-muted)", marginBottom: "var(--space-xs)" }}>
                  Detected Issue
                </h3>
                <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: getConfidenceColor(result.confidence) }}>
                  {result.disease_name}
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: 'var(--space-sm)' }}>
                  <div style={{ width: '100%', height: '6px', background: 'var(--color-bg-secondary)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${result.confidence * 100}%`, height: '100%', background: getConfidenceColor(result.confidence), transition: "width 0.5s ease" }}></div>
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)", minWidth: "50px" }}>
                    {(result.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* All Predictions (Top-K) */}
              {result.all_predictions && result.all_predictions.length > 1 && (
                <div>
                  <h3 style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--color-text-primary)", marginBottom: "var(--space-sm)" }}>
                    All Predictions
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
                    {result.all_predictions.map((pred, i) => (
                      <div key={i} style={{ 
                        display: "flex", alignItems: "center", gap: "var(--space-sm)",
                        padding: "var(--space-sm) var(--space-md)",
                        background: i === 0 ? "rgba(52, 211, 153, 0.08)" : "transparent",
                        borderRadius: "var(--radius-sm)",
                        border: i === 0 ? "1px solid rgba(52, 211, 153, 0.2)" : "1px solid transparent",
                      }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)", minWidth: "20px" }}>
                          #{i + 1}
                        </span>
                        <span style={{ flex: 1, fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                          {pred.class_label}
                        </span>
                        <div style={{ width: "80px", height: "4px", background: "var(--color-bg-secondary)", borderRadius: "2px", overflow: "hidden" }}>
                          <div style={{ width: `${pred.probability * 100}%`, height: "100%", background: getConfidenceColor(pred.probability) }}></div>
                        </div>
                        <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)", minWidth: "45px", textAlign: "right" }}>
                          {(pred.probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Grad-CAM Info */}
              {result.gradcam && (
                <div style={{ 
                  padding: "var(--space-md)", 
                  background: "rgba(96, 165, 250, 0.08)", 
                  border: "1px solid rgba(96, 165, 250, 0.2)", 
                  borderRadius: "var(--radius-md)" 
                }}>
                  <h3 style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--color-text-primary)", marginBottom: "var(--space-xs)", display: "flex", alignItems: "center", gap: "6px" }}>
                    🔥 Grad-CAM Explainability
                  </h3>
                  <p style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                    The Grad-CAM overlay highlights regions of the leaf image that most influenced the model&apos;s decision. 
                    Toggle the heatmap using the button on the image.
                  </p>
                  <p style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "var(--space-xs)" }}>
                    Target layer: {result.gradcam.target_layer || "features.7.0"}
                  </p>
                </div>
              )}
              
              {/* Recommendation */}
              <div>
                <h3 style={{ fontSize: "0.9rem", fontWeight: "600", color: "var(--color-text-primary)", marginBottom: "var(--space-sm)" }}>
                  Recommended Action
                </h3>
                <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
                  {result.recommendation}
                </p>
              </div>
              
              <div style={{ marginTop: "var(--space-sm)", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                Source: {result.source || "Local ML - EfficientNetV2"}
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', opacity: 0.5, textAlign: 'center' }}>
              <div style={{ fontSize: "3rem", marginBottom: "var(--space-md)" }}>🔍</div>
              <p style={{ color: "var(--color-text-secondary)", maxWidth: "200px" }}>Upload an image to see the diagnosis results here.</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

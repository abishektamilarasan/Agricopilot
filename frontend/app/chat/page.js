"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import { useFieldContext } from "../components/FieldContext";

const LocationPicker = dynamic(() => import("../components/LocationPicker"), { ssr: false });

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        `Hello! I'm AgriCopilot, your AI agricultural advisor. I can help with crop management, irrigation scheduling, fertilizer recommendations, disease risk assessment, and market strategies.\n\nTell me about your field (location, crop) or ask me anything about farming!`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const { lat, setLat, lon, setLon, crop, setCrop, soilType, setSoilType } = useFieldContext();
  const [isMapOpen, setIsMapOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMsg = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.content,
          latitude: parseFloat(lat),
          longitude: parseFloat(lon),
          crop,
          country: "India",
          soil_type: soilType,
          conversation_history: messages.slice(-6).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (!resp.ok) throw new Error(`API error: ${resp.status}`);
      const data = await resp.json();

      const assistantMsg = {
        role: "assistant",
        content: data.response,
        confidence: data.confidence,
        sources: data.sources_used,
        dataSummary: data.data_summary,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ Unable to connect to the backend. Please ensure it's running:\n\n\`cd backend && python main.py\`\n\nError: ${e.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{ display: "flex", gap: "var(--space-lg)", height: "calc(100vh - 96px)" }}>
      {/* Chat Panel */}
      <div className="chat-container" style={{ flex: 1 }}>
        <div className="chat-header">
          <span style={{ fontSize: "2rem" }}>🤖</span>
          <div className="chat-header-info">
            <h2>AgriCopilot Chat</h2>
            <p>
              AI-powered agricultural advisor • Data-driven recommendations
            </p>
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-message ${msg.role}`}>
              <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
              {msg.confidence > 0 && (
                <div className="sources">
                  <strong>Confidence:</strong> {Math.round(msg.confidence)}%
                  {msg.sources?.length > 0 && (
                    <> • <strong>Sources:</strong> {msg.sources.join(", ")}</>
                  )}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant">
              <span className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </span>
              <span
                style={{
                  marginLeft: "8px",
                  fontSize: "0.8rem",
                  color: "var(--color-text-muted)",
                }}
              >
                Analyzing data sources...
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <input
            id="chat-input"
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your crops, weather, soil, irrigation..."
            disabled={loading}
          />
          <button
            id="chat-send"
            className="chat-send-btn"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            Send ↗
          </button>
        </div>
      </div>

      {/* Context Sidebar */}
      <LocationPicker 
        isOpen={isMapOpen} 
        onClose={() => setIsMapOpen(false)} 
        initialLat={parseFloat(lat)} 
        initialLon={parseFloat(lon)}
        onSelect={(newLat, newLon, newSoil) => {
          setLat(newLat.toString());
          setLon(newLon.toString());
          if (newSoil) setSoilType(newSoil);
        }}
      />
      
      <div
        style={{
          width: "280px",
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-md)",
          flexShrink: 0,
        }}
      >
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-icon">📍</span> Context
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            <div className="control-group">
              <label className="control-label">Location</label>
              <div style={{ display: "flex", gap: "8px", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ 
                  fontFamily: "var(--font-mono)", 
                  fontSize: "0.85rem",
                  color: "var(--color-text-primary)",
                  display: "flex", flexDirection: "column", gap: "4px"
                }}>
                  <span>{parseFloat(lat).toFixed(4)}°,<br/>{parseFloat(lon).toFixed(4)}°</span>
                  {soilType && (
                    <span style={{ color: "var(--color-emerald-400)", fontSize: "0.75rem", border: "1px solid var(--color-emerald-400)", borderRadius: "4px", padding: "2px 4px", display: "inline-block" }}>
                      {soilType}
                    </span>
                  )}
                </div>
                <button 
                  onClick={() => setIsMapOpen(true)}
                  className="btn-primary"
                  style={{ padding: "4px 8px", background: "var(--color-bg-tertiary)", fontSize: "0.75rem", flexShrink: 0 }}
                  title="Pick on Map"
                >
                  📍 Map
                </button>
              </div>
            </div>
            <div className="control-group">
              <label className="control-label">Crop</label>
              <select
            className="control-select"
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
          >
            <option value="rice">🌾 Rice</option>
            <option value="maize">🌽 Maize</option>
            <option value="millets">🌾 Millets</option>
            <option value="sugarcane">🎋 Sugarcane</option>
            <option value="banana">🍌 Banana</option>
            <option value="cotton">☁️ Cotton</option>
            <option value="groundnut">🥜 Groundnut</option>
            <option value="tomato">🍅 Tomato</option>
            <option value="onion">🧅 Onion</option>
            <option value="mango">🥭 Mango</option>
          </select>
              <p style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginTop: "4px", lineHeight: 1.4 }}>
                🔬 Crop context lets the AI tailor advice on irrigation, fertilizer, disease risk, and market prices to your specific crop.
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-icon">💡</span> Try asking
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            {[
              "Should I irrigate today?",
              "What's the disease risk?",
              "When should I harvest?",
              "Is millet more profitable?",
              "What fertilizer do I need?",
              "How's my soil health?",
            ].map((q, i) => (
              <button
                key={i}
                onClick={() => {
                  setInput(q);
                }}
                style={{
                  background: "var(--color-bg-secondary)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  padding: "var(--space-sm) var(--space-md)",
                  color: "var(--color-text-secondary)",
                  fontSize: "0.78rem",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all var(--transition-base)",
                  fontFamily: "var(--font-sans)",
                }}
                onMouseEnter={(e) => {
                  e.target.style.borderColor = "var(--color-border-hover)";
                  e.target.style.color = "var(--color-text-accent)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.borderColor = "var(--color-border)";
                  e.target.style.color = "var(--color-text-secondary)";
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

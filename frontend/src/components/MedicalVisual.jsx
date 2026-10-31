import React, { useState } from "react";
import brainImg from "../assets/Glossy Neon Gradient Brain.png";

export default function MedicalVisual({ compact = false }) {
  const [heatmapMode, setHeatmapMode] = useState(false);

  return (
    <div className={`med-visual-wrapper ${compact ? "compact" : ""}`}>
      {/* Central 3D Glass Hemisphere & Anatomical Core */}
      <div className="orb-stage">
        {/* Ambient Glows */}
        <div className="ambient-blur blur-cyan" />
        <div className="ambient-blur blur-pink" />
        <div className="ambient-blur blur-lavender" />

        {/* The 3D Glass Pedestal / Hemisphere Container */}
        <div className="glass-orb-container">
          {/* Animated Waveform Floating Card (Top Left) */}
          <div className="floating-card telemetry-card">
            <div className="card-top-label">
              <span className="telemetry-title">Inference Telemetry</span>
              <span className="telemetry-value">38.4 ms</span>
            </div>
            <div className="waveform-container">
              <svg viewBox="0 0 140 40" className="waveform-svg">
                <defs>
                  <linearGradient id="waveGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#3857F5" />
                    <stop offset="50%" stopColor="#818CF8" />
                    <stop offset="100%" stopColor="#38BDF8" />
                  </linearGradient>
                  <linearGradient id="waveGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#F472B6" />
                    <stop offset="50%" stopColor="#FB7185" />
                    <stop offset="100%" stopColor="#FDA4AF" />
                  </linearGradient>
                </defs>
                {/* Dual flowing waves matching reference image */}
                <path
                  d="M0 26 Q 25 10, 50 24 T 100 18 T 140 22"
                  fill="none"
                  stroke="url(#waveGrad1)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  className="wave-path-1"
                />
                <path
                  d="M0 32 Q 35 38, 65 20 T 110 28 T 140 14"
                  fill="none"
                  stroke="url(#waveGrad2)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  className="wave-path-2"
                />
              </svg>
            </div>
            <div className="telemetry-footer">
              <span className="dot pulse-blue"></span>
              <span>TorchScript JIT · ResNet-50</span>
            </div>
          </div>

          {/* Model Confidence Card (Top Right) */}
          <div className="floating-card confidence-card">
            <div className="badge-icon badge-pink">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <div className="badge-content">
              <span className="badge-title">Model Certainty</span>
              <span className="badge-value">98.6% Confident</span>
            </div>
          </div>

          {/* Clinician In Loop Card (Center Right) */}
          <div className="floating-card clinician-card">
            <div className="badge-icon badge-blue">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <div className="badge-content">
              <span className="badge-title">Clinical Review</span>
              <span className="badge-value">Level II Verified</span>
            </div>
          </div>

          {/* The 3D Glass Hemisphere Bowl / Pedestal */}
          <div className="frosted-hemisphere">
            {/* 3D Glossy Neon Gradient Brain Render (User Asset) */}
            <div className={`brain-img-container ${heatmapMode ? "heatmap-active" : ""}`}>
              <img
                src={brainImg}
                alt="3D Glossy Neon Gradient Brain AI Model"
                className="glossy-brain-image"
              />

              {/* Interactive Grad-CAM Heatmap Overlay on the 3D Brain */}
              {heatmapMode && (
                <div className="gradcam-overlay-wrapper">
                  <div className="gradcam-heatmap-blob" />
                  <div className="gradcam-bounding-box">
                    <span className="gradcam-roi-tag">ROI #1 [0.94]</span>
                  </div>
                </div>
              )}
            </div>

            {/* Glass Pedestal Bottom Half (Translucent Hemisphere Shell with rim reflection) */}
            <div className="glass-shell">
              <div className="glass-rim-highlight"></div>
              <div className="glass-inner-shadow"></div>
            </div>

            {/* Interactive "ON!" Status Toggle Switch (Directly from Reference Image) */}
            <div
              className={`pill-switch ${heatmapMode ? "is-active" : ""}`}
              onClick={() => setHeatmapMode(!heatmapMode)}
              title="Click to toggle Explainable Grad-CAM Heatmap overlay"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setHeatmapMode(!heatmapMode); }}
            >
              <div className="switch-top-text">{heatmapMode ? "CAM" : "ON!"}</div>
              <div className="switch-track">
                <div className={`switch-thumb ${heatmapMode ? "active" : ""}`} />
              </div>
            </div>
          </div>
        </div>

        {/* Floor Shadow Reflection */}
        <div className="pedestal-shadow"></div>
      </div>
    </div>
  );
}

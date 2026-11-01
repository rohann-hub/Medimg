import React, { useState } from "react";
import MedicalVisual from "./MedicalVisual.jsx";
import medCrossLogo from "../assets/Blue Gradient Medical Cross Emblem.png";
import orbitalLogo from "../assets/DO! MedImg AI Orbital Logo.png";

export default function LandingPage({ onNavigateLogin }) {
  const [activeStep, setActiveStep] = useState(0);

  const workflowSteps = [
    {
      num: "01",
      title: "Upload DICOM Images",
      desc: "Drag-and-drop raw .dcm files or compressed series archives directly into the browser, synced with Orthanc PACS.",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      ),
    },
    {
      num: "02",
      title: "Process & Validate",
      desc: "Automated ingestion pipeline extracts DICOM tags, verifies modality (DX, CR, CT), and checks pixel spacing.",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      ),
    },
    {
      num: "03",
      title: "Run AI Analysis",
      desc: "TorchScript deep learning vision models execute high-throughput inference in milliseconds on incoming studies.",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      ),
    },
    {
      num: "04",
      title: "Generate Grad-CAM",
      desc: "Visual attribution maps pinpoint the exact anatomical regions and pulmonary opacities informing each finding.",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      ),
    },
    {
      num: "05",
      title: "Doctor Reviews Findings",
      desc: "Radiologists inspect high-res scans, toggle explainability heatmaps, adjust window/level, and compare probabilities.",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      ),
    },
    {
      num: "06",
      title: "Approve or Reject",
      desc: "Clinicians make the final decision with one click, recorded with HMAC-SHA256 cryptography in the immutable audit trail.",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      ),
    },
  ];

  const features = [
    {
      title: "AI-Powered Image Classification",
      desc: "Multi-class deep convolutional networks detect pathologies with calibrated probability confidence scores.",
      badge: "TorchScript JIT",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      ),
    },
    {
      title: "Explainable AI & Grad-CAM Heatmaps",
      desc: "Overlay gradient-weighted class activation mapping to visually inspect the precise neural network reasoning.",
      badge: "Saliency Maps",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      ),
    },
    {
      title: "Medical Image Visualization",
      desc: "Full-fidelity viewport with window/level contrast, pan, zoom, grayscale inversion, and crosshair tools.",
      badge: "Radiology Viewport",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="11" y1="8" x2="11" y2="14" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      ),
    },
    {
      title: "DICOM Upload & Processing",
      desc: "Seamless synchronization with Orthanc DICOM server for standard medical image archiving and routing.",
      badge: "Orthanc PACS",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
      ),
    },
    {
      title: "CT Image Segmentation",
      desc: "Axial slice navigation with interactive scrubber bar, anomaly slice ticks, and multi-slice scan series support.",
      badge: "Volumetric 3D",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
      ),
    },
    {
      title: "Doctor Review & Approval",
      desc: "Clinician-in-the-loop workflow. Approve or reject recommendations with mandatory clinical rationale notes.",
      badge: "Human-In-The-Loop",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      ),
    },
    {
      title: "Study Management & Worklist",
      desc: "Live updating patient worklist with modality filters, inference status chips, and patient de-identification.",
      badge: "Auto-Polling",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="8" y1="6" x2="21" y2="6" />
          <line x1="8" y1="12" x2="21" y2="12" />
          <line x1="8" y1="18" x2="21" y2="18" />
          <line x1="3" y1="6" x2="3.01" y2="6" />
          <line x1="3" y1="12" x2="3.01" y2="12" />
          <line x1="3" y1="18" x2="3.01" y2="18" />
        </svg>
      ),
    },
    {
      title: "Audit Trail & Traceability",
      desc: "Cryptographically verifiable tamper-evident event log securing every user login, inference, and approval.",
      badge: "HMAC-SHA256",
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      ),
    },
  ];

  return (
    <div className="landing-page-root">
      {/* Top Banner: Educational Disclaimer */}
      <div className="global-disclaimer-banner">
        <span className="disclaimer-badge">Clinical Research Notice</span>
        <span>
          <strong>Educational / Research Use Only.</strong> Not a Medical Device. AI output provides clinical decision support and requires validation by a qualified clinician.
        </span>
      </div>

      {/* Main Canvas Container (matches the rounded reference image frame) */}
      <div className="landing-canvas-frame">
        {/* Top Navbar */}
        <header className="landing-nav">
          <div className="nav-brand" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            <img src={medCrossLogo} alt="" className="nav-cross-logo" aria-hidden="true" />
            <img src={orbitalLogo} alt="DO! MedImg AI" className="nav-orbital-logo" />
          </div>

          <nav className="nav-center-links">
            <a href="#hero" className="nav-link">Home</a>
            <a href="#features" className="nav-link">Features</a>
            <a href="#how-it-works" className="nav-link">Workflow</a>
            <a href="#about" className="nav-link">About Us</a>
          </nav>

          <div className="nav-actions">
            <button className="btn-nav-login" onClick={onNavigateLogin}>
              Sign In
            </button>
            <button className="btn-nav-get-started" onClick={onNavigateLogin}>
              Get Started
            </button>
          </div>
        </header>

        {/* Hero Section (Carefully composed according to reference image) */}
        <section id="hero" className="hero-section">
          <div className="hero-content-grid">
            {/* Left Column: Heading, Subtitle, and CTAs */}
            <div className="hero-left-column">
              {/* Badge element inspired by reference image */}
              <div className="hero-badge-pill">
                <div className="pill-dual-circle">
                  <div className="dual-circle-left">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="3">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                    </svg>
                  </div>
                  <div className="dual-circle-right"></div>
                </div>
                <span className="badge-pill-text">
                  We develop revolutionary technologies delivering quality healthcare through medical AI
                </span>
              </div>

              {/* Main Bold Title */}
              <h1 className="hero-main-title">
                Diagnostic<br />Expert System.
              </h1>

              {/* Supporting Subtitle */}
              <p className="hero-description">
                Transform medical imaging workflows with AI-powered image analysis, intelligent classification,
                explainable Grad-CAM heatmaps, and doctor-reviewed clinical decision support.
              </p>

              {/* CTAs */}
              <div className="hero-cta-group">
                <button className="btn-hero-primary" onClick={onNavigateLogin}>
                  Get Started
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>
                <a href="#features" className="btn-hero-secondary">
                  Explore Features
                </a>
              </div>
            </div>

            {/* Right Column: 3D Visual with Floating Cards and Toggle */}
            <div className="hero-right-column">
              <MedicalVisual />
            </div>
          </div>

          {/* Bottom Hero Cards Row (Directly matching reference image layout) */}
          <div className="hero-bottom-cards-row">
            {/* Left Card: Intelligent Adaptive Troubleshooting Assistant */}
            <div className="bottom-card-adaptive">
              <div className="adaptive-art-thumbnail">
                {/* SVG Artistic Anatomical Heart / Thorax with Pastel Swirls */}
                <svg viewBox="0 0 100 100" className="adaptive-svg">
                  <defs>
                    <radialGradient id="artGrad" cx="45%" cy="40%" r="55%">
                      <stop offset="0%" stopColor="#FDE047" stopOpacity="0.8" />
                      <stop offset="35%" stopColor="#FB7185" stopOpacity="0.9" />
                      <stop offset="70%" stopColor="#A855F7" stopOpacity="0.85" />
                      <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.9" />
                    </radialGradient>
                    <filter id="cardGlow">
                      <feGaussianBlur stdDeviation="3" result="glow" />
                      <feComposite in="SourceGraphic" in2="glow" operator="over" />
                    </filter>
                  </defs>
                  <path
                    d="M50 20 C35 5 15 15 15 35 C15 60 50 85 50 85 C50 85 85 60 85 35 C85 15 65 5 50 20 Z"
                    fill="url(#artGrad)"
                    filter="url(#cardGlow)"
                  />
                  <path
                    d="M35 32 Q45 25 55 35 T65 50"
                    fill="none"
                    stroke="rgba(255,255,255,0.7)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  <path
                    d="M40 45 Q50 60 45 70"
                    fill="none"
                    stroke="rgba(255,255,255,0.5)"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <div className="adaptive-text-content">
                <h3 className="adaptive-title">
                  Intelligent Adaptive Troubleshooting Assistant for Fast Issue Resolution
                </h3>
                <p className="adaptive-description">
                  Empowering users with real-time insights, smart diagnostics, and self-evolving solutions.
                </p>
              </div>
            </div>

            {/* Right Card: 4.9* Satisfaction Card */}
            <div className="bottom-card-satisfaction">
              <div className="satisfaction-score">
                <span className="satisfaction-number">4.9</span>
                <span className="satisfaction-star">★</span>
              </div>
              <div className="satisfaction-label">
                USER SATISFACTION LEVEL
              </div>
              <div className="satisfaction-subtext">
                Clinically validated across institutional research datasets
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="section-features">
          <div className="section-header-center">
            <span className="section-kicker">Core Capabilities</span>
            <h2 className="section-title">Designed for Radiological Precision</h2>
            <p className="section-subtitle">
              Engineered from the ground up for high-fidelity medical imaging, clinical traceability, and explainable decision support.
            </p>
          </div>

          <div className="features-grid">
            {features.map((feat, idx) => (
              <div key={idx} className="feature-card">
                <div className="feature-card-header">
                  <div className="feature-icon-box">{feat.icon}</div>
                  <span className="feature-badge">{feat.badge}</span>
                </div>
                <h3 className="feature-title">{feat.title}</h3>
                <p className="feature-desc">{feat.desc}</p>
                <div className="feature-card-footer">
                  <span className="feature-learn-more">Active Module</span>
                  <div className="feature-footer-dot"></div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* How It Works Section */}
        <section id="how-it-works" className="section-how-it-works">
          <div className="section-header-center">
            <span className="section-kicker">End-to-End Workflow</span>
            <h2 className="section-title">From DICOM Ingestion to Clinical Sign-Off</h2>
            <p className="section-subtitle">
              A transparent 6-step diagnostic pipeline that keeps doctors firmly in control of patient outcomes.
            </p>
          </div>

          <div className="workflow-steps-grid">
            {workflowSteps.map((step, idx) => (
              <div
                key={idx}
                className={`workflow-step-card ${activeStep === idx ? "active-step" : ""}`}
                onMouseEnter={() => setActiveStep(idx)}
              >
                <div className="step-number-tag">{step.num}</div>
                <div className="step-icon-wrap">{step.icon}</div>
                <h4 className="step-title">{step.title}</h4>
                <p className="step-desc">{step.desc}</p>
                <div className="step-progress-indicator">
                  <div className="step-progress-bar" style={{ width: `${((idx + 1) / 6) * 100}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* About Section */}
        <section id="about" className="section-about">
          <div className="about-glass-panel">
            <div className="about-text-content">
              <span className="section-kicker">About MedImg AI</span>
              <h2 className="about-heading">Empowering Clinicians, Never Replacing Them</h2>
              <p className="about-paragraph">
                MedImg AI was created to address the growing workload in medical imaging centers by automating initial pathology screening and generating explainable visual heatmaps.
              </p>
              <p className="about-paragraph">
                By presenting calibrated model predictions directly alongside the original scan, our platform equips radiologists with instant second opinions, reducing diagnostic fatigue and accelerating critical triage.
              </p>

              <div className="about-compliance-box">
                <div className="compliance-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3857F5" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                </div>
                <div className="compliance-text">
                  <strong>Educational &amp; Research Focus:</strong> This system is developed for academic evaluation and clinical research workflows. Predictions are strictly decision-support aids requiring qualified clinician sign-off.
                </div>
              </div>
            </div>

            <div className="about-cta-card">
              <h3>Ready to explore MedImg AI?</h3>
              <p>Experience the AI-assisted diagnostic workspace with demo credentials or your own DICOM dataset.</p>
              <button className="btn-hero-primary" onClick={onNavigateLogin}>
                Launch Workspace
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="landing-footer">
          <div className="footer-top-grid">
            <div className="footer-brand-column">
              <div className="footer-brand-head">
                <div className="brand-logo-icon small-icon" aria-hidden="true">
                  <img src={medCrossLogo} alt="MedImg AI Logo" className="brand-logo-img" />
                </div>
                <span className="footer-brand-name">MedImg AI</span>
              </div>
              <p className="footer-tagline">
                Next-generation artificial intelligence for radiological decision support, automated DICOM triage, and explainable Grad-CAM heatmaps.
              </p>

              {/* Social Links: GitHub & LinkedIn */}
              <div className="footer-social-links">
                <a
                  href="https://github.com/rohann-hub"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-social-btn"
                  title="View GitHub Repository"
                  aria-label="GitHub"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  <span>GitHub</span>
                </a>
                <a
                  href="https://www.linkedin.com/in/rupjitshil/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-social-btn"
                  title="View LinkedIn Profile"
                  aria-label="LinkedIn"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                  </svg>
                  <span>LinkedIn</span>
                </a>
              </div>

              <div className="footer-legal-tag">
                Educational / Research Use Only · Not a Medical Device
              </div>
            </div>

            <div className="footer-links-column">
              <h4 className="footer-links-title">Product &amp; Features</h4>
              <ul>
                <li><a href="#features">AI Image Classification</a></li>
                <li><a href="#features">Explainable Heatmaps</a></li>
                <li><a href="#features">DICOM Orthanc PACS</a></li>
                <li><a href="#features">CT Slice Segmentation</a></li>
                <li><a href="#features">Audit Trail Verification</a></li>
              </ul>
            </div>

            <div className="footer-links-column">
              <h4 className="footer-links-title">Platform</h4>
              <ul>
                <li><a href="#how-it-works">Diagnostic Workflow</a></li>
                <li><a href="#about">About Project &amp; Ethics</a></li>
                <li><button className="text-link-btn" onClick={onNavigateLogin}>Sign In to Workspace</button></li>
              </ul>
            </div>
          </div>

          <div className="footer-bottom-bar">
            <span>&copy; {new Date().getFullYear()} MedImg AI Capstone Research. All rights reserved.</span>
            <span>Design & developed by <a href="https://github.com/rohann-hub">rohan</a></span>
          </div>
        </footer>
      </div>
    </div>
  );
}

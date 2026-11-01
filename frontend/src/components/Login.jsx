import React, { useState } from "react";
import { api } from "../api.js";
import MedicalVisual from "./MedicalVisual.jsx";
import medCrossLogo from "../assets/Blue Gradient Medical Cross Emblem.png";
import orbitalLogo from "../assets/DO! MedImg AI Orbital Logo.png";

export default function Login({ onLogin, onNavigateHome }) {
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    if (e) e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const user = await api.login(username, password);
      if (rememberMe) {
        localStorage.setItem("medimg.remembered_user", username);
      } else {
        localStorage.removeItem("medimg.remembered_user");
      }
      onLogin(user);
    } catch (e) {
      setErr(
        e.status === 429
          ? e.message
          : e.status === 401
          ? "Incorrect username or password. Please check your credentials."
          : e.message || "Unable to sign in. Please verify the server is running."
      );
    } finally {
      setBusy(false);
    }
  }


  return (
    <div className="login-page-root">
      {/* Top Banner: Educational Disclaimer */}
      <div className="global-disclaimer-banner">
        <span className="disclaimer-badge">Clinical Research Notice</span>
        <span>
          <strong>Educational / Research Use Only.</strong> Not a Medical Device. Authorized personnel only.
        </span>
      </div>

      <div className="login-container-frame">
        {/* Navigation bar with Back to Website */}
        <header className="login-top-bar">
          <div className="nav-brand" onClick={onNavigateHome} style={{ cursor: "pointer" }}>
            <img src={medCrossLogo} alt="" className="nav-cross-logo" aria-hidden="true" />
            <img src={orbitalLogo} alt="DO! MedImg AI" className="nav-orbital-logo" />
          </div>

          <button className="btn-back-home" onClick={onNavigateHome}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            Back to Website
          </button>
        </header>

        {/* Split-Screen Glass Login Card */}
        <div className="login-split-card">
          {/* Left Column: Form */}
          <div className="login-form-side">
            <div className="login-header-group">
              <div className="login-icon-badge">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3857F5" strokeWidth="2.2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <h2 className="login-heading">Welcome Back</h2>
              <p className="login-subheading">
                Sign in to access your medical imaging workspace and clinical review queue.
              </p>
            </div>

            <form className="login-form-element" onSubmit={submit}>
              <div className="form-field-group">
                <label htmlFor="username-input" className="form-label">
                  Username or Clinician ID
                </label>
                <div className="input-with-icon">
                  <svg className="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                  <input
                    id="username-input"
                    type="text"
                    className="form-input"
                    placeholder="e.g. dr.demo"
                    value={username}
                    onChange={(e) => setU(e.target.value)}
                    autoFocus
                    autoComplete="username"
                    required
                  />
                </div>
              </div>

              <div className="form-field-group">
                <div className="label-with-hint">
                  <label htmlFor="password-input" className="form-label">
                    Password
                  </label>
                </div>
                <div className="input-with-icon">
                  <svg className="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <input
                    id="password-input"
                    type={showPassword ? "text" : "password"}
                    className="form-input"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setP(e.target.value)}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    className="toggle-password-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    title={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              <div className="login-options-row">
                <label className="remember-checkbox-label">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span>Remember username</span>
                </label>
              </div>

              {err && (
                <div className="login-error-alert" role="alert">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{err}</span>
                </div>
              )}

              <button
                type="submit"
                className="btn-login-submit"
                disabled={busy || !username || !password}
              >
                {busy ? (
                  <>
                    <span className="login-spinner"></span>
                    <span>Authenticating...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Workspace</span>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Right Column: Visual Showcase Matching Landing Page Aesthetic */}
          <div className="login-visual-side">
            <div className="login-visual-container">
              <div className="login-visual-header">
                <span className="login-pill-indicator">
                  <span className="live-dot-pulse"></span>
                  Inference Service Online
                </span>
                <span className="login-visual-tag">Orthanc PACS Connected</span>
              </div>

              <div className="login-visual-orb-wrap">
                <MedicalVisual compact={true} />
              </div>

              <div className="login-visual-bottom-card">
                <div className="visual-mini-stat">
                  <span className="mini-stat-num">98.4%</span>
                  <span className="mini-stat-label">Model Certainty</span>
                </div>
                <div className="visual-mini-divider"></div>
                <div className="visual-mini-stat">
                  <span className="mini-stat-num">38ms</span>
                  <span className="mini-stat-label">Median Latency</span>
                </div>
                <div className="visual-mini-divider"></div>
                <div className="visual-mini-stat">
                  <span className="mini-stat-num">100%</span>
                  <span className="mini-stat-label">HMAC Audit Logged</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

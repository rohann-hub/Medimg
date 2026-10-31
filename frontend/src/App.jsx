import React, { useCallback, useEffect, useState } from "react";
import { api, auth } from "./api.js";
import LandingPage from "./components/LandingPage.jsx";
import Login from "./components/Login.jsx";
import Worklist from "./components/Worklist.jsx";
import StudyView from "./components/StudyView.jsx";
import AuditView from "./components/AuditView.jsx";
import UsersView from "./components/UserView.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [info, setInfo] = useState(null);
  const [tab, setTab] = useState("worklist");
  const [studies, setStudies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [view, setView] = useState(() => {
    // If user explicitly navigated to #login, start at login; otherwise start at landing page
    return window.location.hash === "#login" ? "login" : "landing";
  });

  useEffect(() => {
    api.info().then(setInfo).catch(() => {});
    if (auth.refresh) {
      api.me()
        .then((u) => {
          setUser(u);
          setView("workspace");
        })
        .catch(() => auth.set(null));
    }
    const onLogout = () => {
      setUser(null);
      setView("login");
      window.location.hash = "login";
    };
    window.addEventListener("medimg:logout", onLogout);

    const onHashChange = () => {
      if (window.location.hash === "#login") {
        setView("login");
      } else if (window.location.hash === "#home" || window.location.hash === "#landing") {
        setView("landing");
      }
    };
    window.addEventListener("hashchange", onHashChange);

    return () => {
      window.removeEventListener("medimg:logout", onLogout);
      window.removeEventListener("hashchange", onHashChange);
    };
  }, []);

  const refresh = useCallback(() => api.studies().then(setStudies).catch(() => {}), []);
  useEffect(() => {
    if (!user) return;
    refresh();
    const t = setInterval(refresh, 4000); // worklist updates as the worker finishes inference
    return () => clearInterval(t);
  }, [user, refresh]);

  const demo = info?.models?.some((m) => m.is_demo);

  // If unauthenticated: toggle between Landing Page and Login Page
  if (!user) {
    if (view === "login") {
      return (
        <Login
          onLogin={(u) => {
            setUser(u);
            setView("workspace");
            window.location.hash = "";
          }}
          onNavigateHome={() => {
            setView("landing");
            window.location.hash = "";
          }}
        />
      );
    }
    return (
      <LandingPage
        onNavigateLogin={() => {
          setView("login");
          window.location.hash = "login";
        }}
      />
    );
  }

  // Authenticated Medical Review Workspace
  return (
    <div className="app">
      <div className="disclaimer" role="note">
        <strong>Educational / research use only.</strong> Not a medical device. AI output is decision support and
        must be reviewed by a qualified clinician.
      </div>
      {demo && (
        <div className="demo-banner" role="alert">
          An UNTRAINED placeholder model is loaded — predictions are random. Train a model and reload.
        </div>
      )}
      <header className="topbar">
        <div
          className="brand"
          style={{ cursor: "pointer" }}
          onClick={() => setTab("worklist")}
          title="MedImg AI Workspace"
        >
          <span className="brand-mark" aria-hidden="true">◐</span> MedImg <span className="muted">AI Review</span>
        </div>
        <nav>
          <button className={tab === "worklist" ? "active" : ""} onClick={() => setTab("worklist")}>
            Worklist
          </button>
          <button className={tab === "audit" ? "active" : ""} onClick={() => setTab("audit")}>
            Audit trail
          </button>
          {user.role === "admin" && (
            <button className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>
              Users
            </button>
          )}
        </nav>
        <div className="who">
          <button
            className="ghost small landing-link-btn"
            onClick={() => {
              // Allow viewing the landing page without signing out
              setView("landing");
              setUser(null);
            }}
            title="View public landing page"
          >
            Public Site
          </button>
          <span className="mono">{user.username}</span>
          <span className={`role role-${user.role}`}>{user.role}</span>
          <button
            className="ghost"
            onClick={async () => {
              await api.logout();
              setUser(null);
              setSelected(null);
              setTab("worklist");
              setView("login");
              window.location.hash = "login";
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      {tab === "worklist" ? (
        <main className="workspace">
          <Worklist studies={studies} selected={selected} onSelect={setSelected} onUploaded={refresh} user={user} />
          {selected ? (
            <StudyView key={selected} studyId={selected} user={user} onChanged={refresh} />
          ) : (
            <div className="empty">
              <p>Select a study from the worklist, or upload DICOM files.</p>
              <p className="muted small">New studies are analysed automatically once Orthanc marks them complete.</p>
            </div>
          )}
        </main>
      ) : tab === "users" && user.role === "admin" ? (
        <UsersView me={user} />
      ) : (
        <AuditView />
      )}
    </div>
  );
}

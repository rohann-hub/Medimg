import React, { useCallback, useEffect, useState } from "react";
import { api, clearImageCache } from "../api.js";
import ImageViewer from "./ImageViewer.jsx";
import ReviewPanel from "./ReviewPanel.jsx";

export default function StudyView({ studyId, user, onChanged }) {
  const [study, setStudy] = useState(null);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      setStudy(await api.study(studyId));
      setErr("");
    } catch (e) {
      setErr(e.message);
    }
  }, [studyId]);

  useEffect(() => { load(); }, [load]);

  // keep polling while the worker is still analysing this study
  const pending = study && ["queued", "processing"].includes(study.status);
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(() => { clearImageCache(`/studies/${studyId}/`); load(); }, 2500);
    return () => clearInterval(t);
  }, [pending, load, studyId]);

  if (err) return <div className="empty error">{err}</div>;
  if (!study) return <div className="empty muted">Loading…</div>;

  const current = study.predictions.filter((p) => p.is_current);
  const seg = current.find((p) => p.task === "segmentation");

  return (
    <section className="study">
      <div className="viewer-col">
        <div className="study-head">
          <div>
            <h2>
              <span className="mod">{study.modality}</span> Study #{study.id}
            </h2>
            <div className="muted small">
              Pt …{study.patient_ref?.slice(-6) || "—"} · {study.sex || "?"} · {study.age ?? "?"}y ·{" "}
              {study.study_date || "no date"} · {study.description || "No description"}
            </div>
          </div>
          {user.role === "admin" && (
            <button className="ghost" onClick={async () => { await api.reprocess(study.id); clearImageCache(`/studies/${study.id}/`); load(); onChanged(); }}>
              Re-run AI
            </button>
          )}
        </div>
        {pending ? (
          <div className="viewer placeholder"><div className="spinner" /> AI analysis in progress…</div>
        ) : study.status === "failed" ? (
          <div className="viewer placeholder error">Processing failed: {study.error}</div>
        ) : (
          <ImageViewer study={study} segPrediction={seg} />
        )}
      </div>
      <ReviewPanel study={study} predictions={study.predictions} user={user}
                   onDecided={() => { load(); onChanged(); }} />
    </section>
  );
}

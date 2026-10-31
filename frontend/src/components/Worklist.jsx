import React, { useRef, useState } from "react";
import { api } from "../api.js";

const STATUS_LABEL = {
  queued: "Queued",
  processing: "Analysing",
  awaiting_review: "Needs review",
  reviewed: "Reviewed",
  failed: "Failed",
  no_model: "No AI model",
};

export default function Worklist({ studies, selected, onSelect, onUploaded, user }) {
  const input = useRef(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("all");

  async function upload(files) {
    if (!files?.length) return;
    setBusy(true);
    setMsg("");
    try {
      const r = await api.upload(files);
      setMsg(`Sent ${r.accepted} file(s) to Orthanc${r.rejected.length ? `, ${r.rejected.length} rejected` : ""}. Analysis starts when the study is complete.`);
      onUploaded();
    } catch (e) {
      setMsg(`Upload failed: ${e.message}`);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  const shown = studies.filter((s) => filter === "all" || s.status === filter);

  return (
    <aside className="worklist">
      <div
        className={`dropzone ${busy ? "busy" : ""}`}
        onClick={() => input.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); upload([...e.dataTransfer.files]); }}
      >
        <input ref={input} type="file" multiple accept=".dcm,.zip,application/dicom" hidden
               onChange={(e) => upload([...e.target.files])} />
        <strong>{busy ? "Uploading…" : "Upload DICOM"}</strong>
        <span className="muted small">.dcm files or a .zip of a series</span>
      </div>
      {msg && <div className="note small">{msg}</div>}
      <div className="filters">
        {["all", "awaiting_review", "reviewed", "failed"].map((f) => (
          <button key={f} className={filter === f ? "chip active" : "chip"} onClick={() => setFilter(f)}>
            {f === "all" ? "All" : STATUS_LABEL[f]}
          </button>
        ))}
      </div>
      <ul className="study-list">
        {shown.length === 0 && <li className="muted small pad">No studies.</li>}
        {shown.map((s) => (
          <li key={s.id}>
            <button className={`study-row ${selected === s.id ? "sel" : ""}`} onClick={() => onSelect(s.id)}>
              <div className="row1">
                <span className="mod">{s.modality || "—"}</span>
                <span className="mono">#{s.id}</span>
                <span className={`status st-${s.status}`}>{STATUS_LABEL[s.status] || s.status}</span>
              </div>
              <div className="row2 small muted">
                Pt {s.patient_ref ? `…${s.patient_ref.slice(-6)}` : "—"} · {s.sex || "?"} · {s.age ?? "?"}y ·{" "}
                {s.description || "No description"}
              </div>
              {s.ai_summary && (
                <div className={`row3 small ${s.ai_summary.positive ? "pos" : "neg"}`}>
                  AI: {s.ai_summary.positive ? "" : "below threshold — "}{s.ai_summary.label}{" "}
                  {s.ai_summary.task === "classification" && `${Math.round(s.ai_summary.probability * 100)}%`}
                </div>
              )}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}

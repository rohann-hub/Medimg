import React, { useEffect, useState } from "react";
import { api } from "../api.js";

function Prob({ p, threshold }) {
  const pct = Math.round(p * 100);
  return (
    <div className="prob">
      <div className="bar"><div className="fill" style={{ width: `${pct}%` }} />
        {threshold != null && <div className="thr" style={{ left: `${threshold * 100}%` }} title={`threshold ${threshold}`} />}
      </div>
      <span className="mono">{pct}%</span>
    </div>
  );
}

function PredictionCard({ p, user, onDecided }) {
  const [comment, setComment] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const last = p.latest_decision;

  async function decide(d) {
    setBusy(true);
    setErr("");
    try {
      await api.decide(p.id, d, comment || null);
      setComment("");
      onDecided();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`card ${p.is_current ? "" : "superseded"}`}>
      <div className="card-head">
        <span className="kicker">{p.task === "classification" ? "Classification" : "Segmentation"}</span>
        {!p.is_current && <span className="tag">superseded</span>}
      </div>
      {p.task === "classification" ? (
        <>
          <div className={`finding ${p.positive ? "pos" : "neg"}`}>
            {p.positive ? "Possible finding:" : "Below threshold:"} <strong>{p.label}</strong>
          </div>
          {Object.entries(p.details.probabilities || {}).map(([lab, v]) => (
            <div key={lab} className="kv"><span>{lab}</span><Prob p={v} threshold={p.threshold} /></div>
          ))}
          <p className="muted small">
            Confidence is the model's sigmoid output; operating threshold {p.threshold?.toFixed(3)} was chosen on the
            validation set. Heatmap: Grad-CAM — shows where the model looked, not proof of pathology.
          </p>
        </>
      ) : (
        <>
          <div className={`finding ${p.positive ? "pos" : "neg"}`}>
            {p.positive ? <>Segmented <strong>{p.label}</strong></> : <>No <strong>{p.label}</strong> found</>}
          </div>
          <div className="kv"><span>Volume</span><span className="mono">{p.details.volume_ml} mL</span></div>
          <div className="kv"><span>Mean voxel confidence</span><Prob p={p.probability} /></div>
          <div className="kv"><span>Slices with mask</span><span className="mono">{p.details.slices_with_mask?.length ?? 0}</span></div>
        </>
      )}
      <dl className="meta small">
        <dt>Model</dt><dd className="mono">{p.model_version}</dd>
        <dt>Weights SHA-256</dt><dd className="mono" title={p.model_sha256}>{p.model_sha256.slice(0, 16)}…</dd>
        <dt>Inference</dt><dd className="mono">{p.inference_ms} ms · {new Date(p.created_at).toLocaleString()}</dd>
      </dl>

      {p.is_current && (
        <div className="decide">
          {last && (
            <div className={`decision-banner d-${last.decision}`}>
              {last.decision === "approve" ? "Approved" : "Rejected"} by <strong>{last.reviewer}</strong>{" "}
              · {new Date(last.created_at).toLocaleString()}
              {last.comment && <div className="small">“{last.comment}”</div>}
            </div>
          )}
          {user.role === "clinician" ? (
            <>
              <textarea placeholder={last ? "Comment (to change the decision)" : "Clinical comment (required to reject)"}
                        value={comment} onChange={(e) => setComment(e.target.value)} rows={2} maxLength={2000} />
              <div className="btns">
                <button className="approve" disabled={busy} onClick={() => decide("approve")}>Approve AI result</button>
                <button className="reject" disabled={busy || !comment.trim()} onClick={() => decide("reject")}
                        title={!comment.trim() ? "Add a comment explaining the rejection" : ""}>Reject</button>
              </div>
            </>
          ) : (
            <p className="muted small">Only clinicians can approve or reject.</p>
          )}
          {err && <div className="error small">{err}</div>}
        </div>
      )}
      {p.decisions.length > 1 && (
        <details className="history small">
          <summary>Decision history ({p.decisions.length})</summary>
          <ol>
            {p.decisions.map((d) => (
              <li key={d.id}><span className={`dot d-${d.decision}`} /> {d.decision} — {d.reviewer},{" "}
                {new Date(d.created_at).toLocaleString()}{d.comment ? `: ${d.comment}` : ""}</li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function StudyAudit({ studyId, predIds, refreshKey }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    Promise.all([
      api.audit({ entity_type: "study", entity_id: String(studyId), limit: 50 }),
      ...predIds.map((id) => api.audit({ entity_type: "prediction", entity_id: String(id), limit: 50 })),
    ]).then((rs) => setRows(rs.flat().sort((a, b) => b.id - a.id))).catch(() => {});
  }, [studyId, predIds.join(","), refreshKey]);
  return (
    <div className="card">
      <div className="card-head"><span className="kicker">Audit trail for this study</span></div>
      <ul className="audit-mini small">
        {rows.map((r) => (
          <li key={r.id}>
            <span className="mono muted">{new Date(r.ts).toLocaleTimeString()}</span>{" "}
            <strong>{r.actor}</strong> {r.action.replaceAll("_", " ")}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ReviewPanel({ study, predictions, user, onDecided }) {
  const ordered = [...predictions].sort((a, b) => (b.is_current - a.is_current) || b.id - a.id);
  const refreshKey = predictions.map((p) => p.decisions.length).join(",") + study.status;
  return (
    <aside className="review">
      {ordered.length === 0 && (
        <div className="card muted small">
          {study.status === "no_model" ? (study.error || "No AI model is configured for this modality — image is viewable only.") : "No AI result yet."}
        </div>
      )}
      {ordered.map((p) => <PredictionCard key={p.id} p={p} user={user} onDecided={onDecided} />)}
      <StudyAudit studyId={study.id} predIds={predictions.map((p) => p.id)} refreshKey={refreshKey} />
    </aside>
  );
}

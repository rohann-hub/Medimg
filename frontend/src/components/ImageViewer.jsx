import React, { useEffect, useRef, useState } from "react";
import { imageUrl } from "../api.js";

function useAuthedImage(path) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let live = true;
    if (!path) { setUrl(null); return; }
    imageUrl(path).then((u) => live && setUrl(u)).catch(() => live && setUrl(null));
    return () => { live = false; };
  }, [path]);
  return url;
}

export default function ImageViewer({ study, segPrediction }) {
  const volume = study.has_slices;
  const n = study.n_slices || 1;
  const firstMasked = segPrediction?.details?.slices_with_mask?.[0];
  const [slice, setSlice] = useState(firstMasked ?? Math.floor(n / 2));
  const [showOverlay, setShowOverlay] = useState(true);
  const [opacity, setOpacity] = useState(0.5);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef(null);
  const stage = useRef(null);

  const basePath = volume ? `/studies/${study.id}/slices/${slice}.png` : study.has_image ? `/studies/${study.id}/image.png` : null;
  const overlayPath = volume
    ? segPrediction && `/studies/${study.id}/slices/${slice}.png?layer=mask`
    : study.has_heatmap && `/studies/${study.id}/heatmap.png`;
  const base = useAuthedImage(basePath);
  const overlay = useAuthedImage(overlayPath || null);

  // preload neighbours so scrolling through a CT feels instant
  useEffect(() => {
    if (!volume) return;
    for (const k of [slice - 1, slice + 1]) if (k >= 0 && k < n) imageUrl(`/studies/${study.id}/slices/${k}.png`).catch(() => {});
  }, [slice, volume, n, study.id]);

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      if (volume && !e.ctrlKey) setSlice((s) => Math.min(n - 1, Math.max(0, s + Math.sign(e.deltaY))));
      else setZoom((z) => Math.min(8, Math.max(0.5, z * (e.deltaY < 0 ? 1.1 : 0.9))));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [volume, n]);

  const reset = () => { setZoom(1); setPan({ x: 0, y: 0 }); setBrightness(100); setContrast(100); };
  const transform = `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`;

  return (
    <div className="viewer">
      <div className="toolbar">
        <label className="tog">
          <input type="checkbox" checked={showOverlay} onChange={(e) => setShowOverlay(e.target.checked)} />
          {volume ? "Segmentation mask" : "Grad-CAM heatmap"}
        </label>
        <label>Opacity <input type="range" min="0" max="1" step="0.05" value={opacity} disabled={!showOverlay}
                              onChange={(e) => setOpacity(+e.target.value)} /></label>
        <label>Brightness <input type="range" min="40" max="200" value={brightness} onChange={(e) => setBrightness(+e.target.value)} /></label>
        <label>Contrast <input type="range" min="40" max="250" value={contrast} onChange={(e) => setContrast(+e.target.value)} /></label>
        <button className="ghost small" onClick={reset}>Reset view</button>
      </div>
      <div
        className="stage"
        ref={stage}
        tabIndex={0}
        onKeyDown={(e) => {
          if (!volume) return;
          if (e.key === "ArrowUp") setSlice((s) => Math.max(0, s - 1));
          if (e.key === "ArrowDown") setSlice((s) => Math.min(n - 1, s + 1));
        }}
        onMouseDown={(e) => { drag.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }; }}
        onMouseMove={(e) => { if (drag.current) setPan({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y }); }}
        onMouseUp={() => { drag.current = null; }}
        onMouseLeave={() => { drag.current = null; }}
      >
        <div className="layers" style={{ transform }}>
          {base && <img src={base} alt="scan" draggable={false}
                        style={{ filter: `brightness(${brightness}%) contrast(${contrast}%)` }} />}
          {overlay && showOverlay && <img className="overlay" src={overlay} alt="AI overlay" draggable={false}
                                          style={{ opacity }} />}
        </div>
        <div className="corner tl mono small">{study.modality} · {volume ? `slice ${slice + 1}/${n}` : "single image"}</div>
        <div className="corner br mono small">zoom {zoom.toFixed(1)}×</div>
        {!volume && showOverlay && overlay && (
          <div className="legend small"><span>low</span><div className="jet" /><span>high influence</span></div>
        )}
      </div>
      {volume && (
        <div className="slicebar">
          <input type="range" min="0" max={n - 1} value={slice} onChange={(e) => setSlice(+e.target.value)} />
          {segPrediction?.details?.slices_with_mask?.length > 0 && (
            <div className="ticks">
              {segPrediction.details.slices_with_mask.map((k) => (
                <span key={k} style={{ left: `${(k / Math.max(1, n - 1)) * 100}%` }} />
              ))}
            </div>
          )}
          <div className="muted small">Scroll / ↑↓ to change slice · Ctrl+scroll to zoom · drag to pan</div>
        </div>
      )}
    </div>
  );
}

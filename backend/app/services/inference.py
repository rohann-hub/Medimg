"""Model registry + study processing: Orthanc study → AI outputs → database + PNG artifacts."""
from __future__ import annotations

import hashlib
import logging
import shutil
import time
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from medai.dicom_io import PROJECTION_MODALITIES, demographics, load_series, read_dataset, to_display_array
from medai.models import load_checkpoint
from medai.overlay import gray_png, heatmap_png, mask_png
from medai.predict import classify, segment

from . import audit
from ..core.config import settings
from ..db.db import Prediction, Study
from .orthanc import Orthanc

log = logging.getLogger("inference")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Registry:
    """Loads checkpoints once. The SHA-256 of the weights file goes into every prediction row,
    so an auditor can prove exactly which model produced a result."""

    def __init__(self) -> None:
        self.cls = self.seg = None
        self.cls_meta: dict = {}
        self.seg_meta: dict = {}
        self.reload()

    def reload(self) -> None:
        if settings.cls_model_path.exists():
            self.cls, self.cls_meta = load_checkpoint(settings.cls_model_path)
            self.cls_meta["sha256"] = _sha256(settings.cls_model_path)
            log.info("classifier loaded: %s", self.cls_meta["model_version"])
        else:
            log.warning("no classifier at %s — run ml/scripts/make_demo_model.py or train one", settings.cls_model_path)
        if settings.seg_model_path.exists():
            self.seg, self.seg_meta = load_checkpoint(settings.seg_model_path)
            self.seg_meta["sha256"] = _sha256(settings.seg_model_path)
            log.info("segmentation loaded: %s", self.seg_meta["model_version"])

    def describe(self) -> list[dict]:
        out = []
        for m, meta in ((self.cls, self.cls_meta), (self.seg, self.seg_meta)):
            if m is not None:
                out.append({k: meta.get(k) for k in ("task", "arch", "labels", "model_version", "trained_on",
                                                     "threshold", "val_auroc", "val_dice", "sha256")}
                           | {"is_demo": str(meta.get("model_version", "")).startswith("DEMO")})
        return out


def patient_ref(pid: str | None) -> str | None:
    if not pid:
        return None
    return hashlib.sha256((settings.patient_salt + pid).encode()).hexdigest()[:10]


def artifact_dir(study_id: int) -> Path:
    d = settings.artifact_dir / str(study_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _supersede(db: Session, study: Study) -> None:
    for p in study.predictions:
        p.is_current = False


def process_study(db: Session, reg: Registry, orthanc: Orthanc, orthanc_study_id: str, actor: str = "system") -> Study:
    study = db.query(Study).filter_by(orthanc_id=orthanc_study_id).one_or_none()
    if study is None:
        study = Study(orthanc_id=orthanc_study_id)
        db.add(study)
    study.status, study.error = "processing", None
    db.commit()
    try:
        series = orthanc.study_series(orthanc_study_id)
        if not series:
            raise ValueError("study has no series")
        # Pick the series with the most instances (the main acquisition, not a scout/localiser)
        series.sort(key=lambda s: len(s.get("Instances", [])), reverse=True)
        main = series[0]
        modality = main["MainDicomTags"].get("Modality", "OT")
        instances = orthanc.series_instances(main["ID"])
        first = read_dataset(orthanc.instance_file(instances[0]["ID"]))
        info = demographics(first)
        study.study_uid = str(getattr(first, "StudyInstanceUID", "")) or None
        study.patient_ref = patient_ref(str(getattr(first, "PatientID", "")) or None)
        study.sex, study.age, study.modality = info["sex"], info["age"], modality
        study.description = str(getattr(first, "StudyDescription", "") or "")[:256] or None
        study.study_date = str(getattr(first, "StudyDate", "") or "") or None
        out = artifact_dir(study.id)
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

        if modality in PROJECTION_MODALITIES or len(instances) == 1:
            img = to_display_array(first)
            (out / "image.png").write_bytes(gray_png(img))
            study.n_slices = 1
            if reg.cls is None:
                study.status = "no_model"
            else:
                t0 = time.perf_counter()
                res = classify(reg.cls, reg.cls_meta, img)
                ms = int((time.perf_counter() - t0) * 1000)
                (out / "heatmap.png").write_bytes(heatmap_png(res.cam, img.shape))
                _supersede(db, study)
                pred = Prediction(study_id=study.id, task="classification", model_version=reg.cls_meta["model_version"],
                                  model_sha256=reg.cls_meta["sha256"], label=res.top_label, probability=res.top_probability,
                                  threshold=float(reg.cls_meta.get("threshold", 0.5)), positive=res.positive,
                                  details={"probabilities": res.probabilities, "explainer": "Grad-CAM",
                                           "view": info["view"], "image_shape": list(img.shape)},
                                  inference_ms=ms)
                db.add(pred)
                db.flush()
                study.status = "awaiting_review"
                audit.log(db, actor, "inference_completed", "prediction", pred.id,
                          {"study_id": study.id, "model_version": pred.model_version, "model_sha256": pred.model_sha256,
                           "label": pred.label, "probability": pred.probability, "positive": pred.positive,
                           "threshold": pred.threshold, "inference_ms": ms})
        else:
            datasets = [read_dataset(orthanc.instance_file(i["ID"])) for i in instances]
            vol = load_series(datasets)
            study.n_slices = vol.data.shape[0]
            # display window: CT soft tissue (W400/L40); MR has no absolute units → robust percentiles
            lo, hi = (-160.0, 240.0) if modality == "CT" else tuple(np.percentile(vol.data, [1, 99]))
            disp = np.clip((vol.data - lo) / max(1e-6, hi - lo), 0, 1)
            sl = out / "slices"
            sl.mkdir()
            for k in range(study.n_slices):
                (sl / f"{k:04d}.png").write_bytes(gray_png(disp[k], max_side=None))
            if reg.seg is None or modality != "CT":
                study.status = "no_model"
            else:
                t0 = time.perf_counter()
                res = segment(reg.seg, reg.seg_meta, vol.data, vol.spacing)
                ms = int((time.perf_counter() - t0) * 1000)
                mk = out / "mask"
                mk.mkdir()
                for k in range(study.n_slices):
                    if res.mask[k].any():
                        (mk / f"{k:04d}.png").write_bytes(mask_png(res.mask[k]))
                np.savez_compressed(out / "mask.npz", mask=res.mask)
                slices_with_mask = [int(k) for k in np.where(res.mask.reshape(res.mask.shape[0], -1).any(1))[0]]
                _supersede(db, study)
                pred = Prediction(study_id=study.id, task="segmentation", model_version=reg.seg_meta["model_version"],
                                  model_sha256=reg.seg_meta["sha256"], label=reg.seg_meta["labels"][1],
                                  probability=res.mean_confidence, threshold=None, positive=res.voxel_count > 0,
                                  details={"volume_ml": res.volume_ml, "voxels": res.voxel_count,
                                           "slices_with_mask": slices_with_mask, "spacing_zyx_mm": list(vol.spacing),
                                           "explainer": "segmentation mask overlay"},
                                  inference_ms=ms)
                db.add(pred)
                db.flush()
                study.status = "awaiting_review"
                audit.log(db, actor, "inference_completed", "prediction", pred.id,
                          {"study_id": study.id, "model_version": pred.model_version, "model_sha256": pred.model_sha256,
                           "label": pred.label, "volume_ml": res.volume_ml, "mean_confidence": res.mean_confidence,
                           "inference_ms": ms})
        db.commit()
    except Exception as e:  # keep the worker alive; surface the error in the worklist
        log.exception("processing failed for %s", orthanc_study_id)
        db.rollback()
        study.status, study.error = "failed", f"{type(e).__name__}: {e}"[:2000]
        db.commit()
        audit.log(db, actor, "inference_failed", "study", study.id, {"error": study.error})
    return study

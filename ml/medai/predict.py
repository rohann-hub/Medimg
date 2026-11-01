"""Inference entry points shared by evaluation scripts and the backend."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .gradcam import GradCAM
from .models import gradcam_target_layer
from .transforms import letterbox_box, preprocess_2d, preprocess_ct, xyz_ras_to_zyx_lps


@dataclass
class ClassificationResult:
    probabilities: dict[str, float]
    top_label: str
    top_probability: float
    positive: bool  # top_probability >= operating threshold
    cam: np.ndarray  # (H,W) in [0,1], aligned to the *original* image


def classify(model: torch.nn.Module, meta: dict, img01: np.ndarray, with_cam: bool = True) -> ClassificationResult:
    size = int(meta.get("image_size", 320))
    x = preprocess_2d(img01, size)[None]
    labels = meta["labels"]
    if with_cam:
        cam_engine = GradCAM(model, gradcam_target_layer(model, meta["arch"]))
        try:
            probs_t = None
            cams = []
            for i in range(len(labels)):
                cam, logits = cam_engine(x, class_idx=i)
                cams.append(cam)
                probs_t = torch.sigmoid(logits[0])
        finally:
            cam_engine.remove()
    else:
        with torch.no_grad():
            probs_t = torch.sigmoid(model(x)[0])
        cams = [np.zeros((size, size), np.float32)]
    probs = probs_t.numpy().astype(float)  # type: ignore[union-attr]
    top = int(np.argmax(probs))
    # crop letterbox padding away so the heatmap aligns with the original image
    t, l, h, w = letterbox_box(*img01.shape, size)
    cam = cams[top][t : t + h, l : l + w]
    thr = float(meta.get("threshold", 0.5))
    return ClassificationResult(
        probabilities={lab: round(float(p), 4) for lab, p in zip(labels, probs)},
        top_label=labels[top],
        top_probability=round(float(probs[top]), 4),
        positive=bool(probs[top] >= thr),
        cam=cam,
    )


@dataclass
class SegmentationResult:
    mask: np.ndarray  # (Z,Y,X) uint8 in ORIGINAL volume geometry
    voxel_count: int
    volume_ml: float
    mean_confidence: float


def segment(model: torch.nn.Module, meta: dict, volume_hu: np.ndarray, spacing_zyx) -> SegmentationResult:
    from monai.inferers import sliding_window_inference

    x, ras_shape = preprocess_ct(volume_hu, tuple(spacing_zyx))
    roi = tuple(meta.get("roi_size", (96, 96, 96)))
    with torch.no_grad():
        logits = sliding_window_inference(x, roi_size=roi, sw_batch_size=2, predictor=model, overlap=0.25)
        logits = torch.nn.functional.interpolate(logits, size=ras_shape, mode="trilinear", align_corners=False)
        prob = torch.softmax(logits, dim=1)[0]
    fg = prob[1].numpy()
    mask_ras = (prob.argmax(0) == 1).numpy().astype(np.uint8)
    mask = xyz_ras_to_zyx_lps(mask_ras)
    n = int(mask.sum())
    voxel_ml = float(np.prod(spacing_zyx)) / 1000.0
    conf = float(fg[mask_ras.astype(bool)].mean()) if n else 0.0
    return SegmentationResult(mask=mask, voxel_count=n, volume_ml=round(n * voxel_ml, 2), mean_confidence=round(conf, 4))

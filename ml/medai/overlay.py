"""Turn arrays into PNGs for the viewer."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image


def _jet(x: np.ndarray) -> np.ndarray:
    """Jet colormap without matplotlib. x in [0,1] → (H,W,3) uint8."""
    r = np.clip(1.5 - np.abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * x - 1), 0, 1)
    return (np.stack([r, g, b], -1) * 255).astype(np.uint8)


def gray_png(img01: np.ndarray, max_side: int | None = 1024) -> bytes:
    im = Image.fromarray((np.clip(img01, 0, 1) * 255).astype(np.uint8), mode="L")
    if max_side and max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def heatmap_png(cam01: np.ndarray, size_hw: tuple[int, int], min_alpha_at: float = 0.2) -> bytes:
    """RGBA heatmap with transparency proportional to activation.

    The frontend stacks this over the grayscale scan and controls overall opacity,
    so the doctor can fade the AI explanation in and out.
    """
    h, w = size_hw
    cam = np.asarray(Image.fromarray((cam01 * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)) / 255.0
    rgb = _jet(cam)
    alpha = np.clip((cam - min_alpha_at) / (1 - min_alpha_at), 0, 1)
    rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def mask_png(mask: np.ndarray, color=(0, 220, 120), alpha: int = 140) -> bytes:
    """Binary segmentation mask → RGBA PNG (transparent where mask == 0)."""
    m = mask.astype(bool)
    rgba = np.zeros((*m.shape, 4), dtype=np.uint8)
    rgba[m] = (*color, alpha)
    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG", optimize=True)
    return buf.getvalue()

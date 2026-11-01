"""Preprocessing + augmentation. The *eval* transform is what the backend uses."""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def preprocess_2d(img: np.ndarray, size: int = 320) -> torch.Tensor:
    """[0,1] grayscale (H,W) → normalized (3,size,size) tensor for an ImageNet-pretrained CNN.

    Aspect ratio is preserved with letterbox padding so anatomy is not squashed.
    """
    t = torch.from_numpy(np.ascontiguousarray(img, dtype=np.float32))[None, None]
    h, w = t.shape[-2:]
    scale = size / max(h, w)
    nh, nw = max(1, round(h * scale)), max(1, round(w * scale))
    t = F.interpolate(t, size=(nh, nw), mode="bilinear", align_corners=False)
    pad_h, pad_w = size - nh, size - nw
    t = F.pad(t, (pad_w // 2, pad_w - pad_w // 2, pad_h // 2, pad_h - pad_h // 2), value=0.0)
    t = t.repeat(1, 3, 1, 1)[0]
    mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
    return (t - mean) / std


def letterbox_box(h: int, w: int, size: int) -> tuple[int, int, int, int]:
    """Region (top, left, height, width) of the real image inside the letterboxed tensor."""
    scale = size / max(h, w)
    nh, nw = max(1, round(h * scale)), max(1, round(w * scale))
    return (size - nh) // 2, (size - nw) // 2, nh, nw


def train_augment_2d(size: int = 320):
    """Mild, anatomically plausible augmentation for chest X-rays.

    No vertical flips (anatomy is not symmetric top-bottom); horizontal flips
    are debatable (heart side) so they are off by default.
    """
    import torchvision.transforms.v2 as T

    return T.Compose(
        [
            T.RandomAffine(degrees=7, translate=(0.05, 0.05), scale=(0.92, 1.08)),
            T.ColorJitter(brightness=0.15, contrast=0.15),
            T.RandomApply([T.GaussianBlur(kernel_size=3, sigma=(0.1, 0.8))], p=0.2),
        ]
    )


# ---------- 3D (CT) ----------

CT_WINDOW = (-57.0, 164.0)  # abdominal soft-tissue window used by MONAI's spleen tutorial
SEG_SPACING_XYZ = (1.5, 1.5, 2.0)  # mm — must match Spacingd(pixdim=...) in train_segmentation.py

# Orientation: MONAI training loads NIfTI and reorients to RAS with array order (X, Y, Z).
# DICOM slices stacked by dicom_io.load_series are (Z, Y, X) in LPS (+col → patient Left,
# +row → Posterior, +slice → Superior for standard axial acquisitions).
# The helpers below convert between the two so train and serve see the same anatomy layout.


def zyx_lps_to_xyz_ras(vol: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(vol.transpose(2, 1, 0)[::-1, ::-1, :])


def xyz_ras_to_zyx_lps(vol: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(vol[::-1, ::-1, :].transpose(2, 1, 0))


def preprocess_ct(volume_hu_zyx: np.ndarray, spacing_zyx: tuple[float, float, float]) -> tuple[torch.Tensor, tuple[int, int, int]]:
    """DICOM HU volume (Z,Y,X) → (1,1,X,Y,Z) RAS tensor, windowed to [0,1], resampled to SEG_SPACING_XYZ.

    Returns the tensor and the RAS shape *before* resampling (for mapping the mask back).
    """
    lo, hi = CT_WINDOW
    v = zyx_lps_to_xyz_ras(volume_hu_zyx)
    v = np.clip((v - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)
    spacing_xyz = (spacing_zyx[2], spacing_zyx[1], spacing_zyx[0])
    t = torch.from_numpy(v)[None, None]
    new_shape = [max(1, round(s * sp / tsp)) for s, sp, tsp in zip(v.shape, spacing_xyz, SEG_SPACING_XYZ)]
    return F.interpolate(t, size=new_shape, mode="trilinear", align_corners=False), tuple(v.shape)  # type: ignore[return-value]

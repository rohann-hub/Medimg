"""DICOM reading helpers.

A DICOM file = a header of tagged metadata (patient, study, series, geometry,
pixel encoding) + a pixel array. The things that bite people:

* Pixel values are stored raw. Real units come from RescaleSlope/Intercept
  (CT → Hounsfield Units).
* MONOCHROME1 means "0 is white" — must be inverted to look like MONOCHROME2.
* X-rays often carry a VOI LUT / WindowCenter+Width that tells you how to map
  12-16 bit values to a displayable range.
* A CT/MR "scan" is a *series* of single-slice files. Slice order must come
  from ImagePositionPatient, never from file names or InstanceNumber alone.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pydicom
from pydicom.dataset import Dataset

try:  # optional in older pydicom versions
    from pydicom.pixels import apply_voi_lut
except ImportError:  # pragma: no cover
    from pydicom.pixel_data_handlers.util import apply_voi_lut  # type: ignore

PROJECTION_MODALITIES = {"CR", "DX", "DR", "RG", "MG", "XA"}
VOLUME_MODALITIES = {"CT", "MR", "PT"}


def read_dataset(src: str | Path | bytes) -> Dataset:
    if isinstance(src, (bytes, bytearray)):
        return pydicom.dcmread(io.BytesIO(src), force=True)
    return pydicom.dcmread(str(src), force=True)


def to_display_array(ds: Dataset) -> np.ndarray:
    """2D image → float32 in [0, 1], MONOCHROME2 orientation, VOI LUT applied.

    Used for X-rays (training and inference) and for thumbnails.
    """
    arr = ds.pixel_array
    if arr.ndim == 3 and getattr(ds, "SamplesPerPixel", 1) == 3:  # RGB secondary capture
        arr = arr.mean(axis=-1)
    elif arr.ndim == 3:  # multi-frame: take middle frame
        arr = arr[arr.shape[0] // 2]
    arr = arr.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    arr = arr * slope + intercept
    try:
        if "VOILUTSequence" in ds or "WindowCenter" in ds:
            arr = apply_voi_lut(arr, ds).astype(np.float32)
    except Exception:
        pass  # fall back to robust min/max below
    lo, hi = np.percentile(arr, [0.5, 99.5])
    if hi <= lo:
        hi = lo + 1.0
    arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
    if str(getattr(ds, "PhotometricInterpretation", "MONOCHROME2")).upper() == "MONOCHROME1":
        arr = 1.0 - arr
    return arr.astype(np.float32)


@dataclass
class Volume:
    """A 3D scan assembled from a DICOM series. data is (Z, Y, X) in real units (HU for CT)."""

    data: np.ndarray
    spacing: tuple[float, float, float]  # (z, y, x) in mm
    modality: str
    meta: dict = field(default_factory=dict)


def load_series(datasets: Iterable[Dataset]) -> Volume:
    """Stack single-slice datasets of one series into a correctly ordered volume."""
    slices = [d for d in datasets if hasattr(d, "PixelData")]
    if not slices:
        raise ValueError("series has no pixel data")
    if all(hasattr(d, "ImagePositionPatient") and hasattr(d, "ImageOrientationPatient") for d in slices):
        iop = np.array(slices[0].ImageOrientationPatient, dtype=float)
        normal = np.cross(iop[:3], iop[3:])
        slices.sort(key=lambda d: float(np.dot(normal, np.array(d.ImagePositionPatient, dtype=float))))
        pos = [float(np.dot(normal, np.array(d.ImagePositionPatient, dtype=float))) for d in slices]
        dz = float(np.median(np.diff(pos))) if len(pos) > 1 else float(getattr(slices[0], "SliceThickness", 1.0))
    else:
        slices.sort(key=lambda d: int(getattr(d, "InstanceNumber", 0)))
        dz = float(getattr(slices[0], "SliceThickness", 1.0) or 1.0)
    stack = []
    for d in slices:
        a = d.pixel_array.astype(np.float32)
        a = a * float(getattr(d, "RescaleSlope", 1) or 1) + float(getattr(d, "RescaleIntercept", 0) or 0)
        stack.append(a)
    data = np.stack(stack, axis=0)
    py, px = (float(v) for v in getattr(slices[0], "PixelSpacing", [1.0, 1.0]))
    return Volume(
        data=data,
        spacing=(abs(dz) or 1.0, py, px),
        modality=str(getattr(slices[0], "Modality", "OT")),
        meta={"n_slices": len(slices)},
    )


def demographics(ds: Dataset) -> dict:
    """Pull the fields used for subgroup (bias) analysis. Missing values stay None."""
    age = None
    raw = str(getattr(ds, "PatientAge", "") or "")
    if raw[:-1].isdigit():
        n, unit = int(raw[:-1]), raw[-1].upper()
        age = n if unit == "Y" else round(n / 12, 1) if unit == "M" else round(n / 52, 1) if unit == "W" else round(n / 365, 1)
    sex = str(getattr(ds, "PatientSex", "") or "").upper() or None
    return {
        "age": age,
        "sex": sex if sex in {"M", "F", "O"} else None,
        "view": str(getattr(ds, "ViewPosition", "") or "") or None,
        "manufacturer": str(getattr(ds, "Manufacturer", "") or "") or None,
    }

"""Generate SYNTHETIC DICOM files for smoke-testing the pipeline (no patient data involved).

    python ml/scripts/make_sample_dicoms.py --out samples
      → samples/synthetic_cxr_1.dcm, synthetic_cxr_2.dcm  (DX, 1024x1024, 12-bit)
      → samples/synthetic_ct/slice_000.dcm ...           (CT series, 40 slices, HU)

For realistic demos, upload real de-identified DICOMs from RSNA / TCIA instead.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, DigitalXRayImageStorageForPresentation, ExplicitVRLittleEndian, generate_uid


def _base(path: Path, sop_class, modality: str, study_uid: str, series_uid: str, pid: str, sex: str, age: str):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = sop_class
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID, ds.SOPInstanceUID = sop_class, meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID, ds.SeriesInstanceUID = study_uid, series_uid
    ds.Modality, ds.PatientID, ds.PatientName = modality, pid, f"SYNTHETIC^{pid}"
    ds.PatientSex, ds.PatientAge = sex, age
    ds.StudyDate = dt.date.today().strftime("%Y%m%d")
    ds.StudyDescription = f"SYNTHETIC {modality} - not a real patient"
    ds.Manufacturer = "medimg-capstone synthetic generator"
    ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 12, 11
    return ds


def synthetic_cxr(rng, size=1024, opacity=True) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size] / size
    body = np.exp(-(((xx - 0.5) / 0.42) ** 2 + ((yy - 0.55) / 0.5) ** 2) ** 3)
    lungs = sum(np.exp(-(((xx - cx) / 0.15) ** 2 + ((yy - 0.48) / 0.27) ** 2) ** 2) for cx in (0.32, 0.68))
    heart = np.exp(-(((xx - 0.55) / 0.12) ** 2 + ((yy - 0.62) / 0.12) ** 2) ** 2)
    img = 0.75 * body - 0.55 * lungs + 0.35 * heart
    for k in range(10):  # ribs
        img += 0.06 * np.exp(-((yy - 0.25 - 0.055 * k - 0.08 * (xx - 0.5) ** 2) / 0.008) ** 2) * lungs
    if opacity:
        img += 0.35 * np.exp(-(((xx - 0.7) / 0.07) ** 2 + ((yy - 0.6) / 0.08) ** 2))
    img += rng.normal(0, 0.015, img.shape)
    img = (img - img.min()) / (img.max() - img.min())
    return (img * 4095).astype(np.uint16)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="samples")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)

    for i, (opac, sex, age) in enumerate([(True, "F", "054Y"), (False, "M", "032Y")], 1):
        p = out / f"synthetic_cxr_{i}.dcm"
        ds = _base(p, DigitalXRayImageStorageForPresentation, "DX", generate_uid(), generate_uid(), f"SYN-CXR-{i:03d}", sex, age)
        px = synthetic_cxr(rng, opacity=opac)
        ds.Rows, ds.Columns = px.shape
        ds.PixelRepresentation, ds.PixelSpacing, ds.ViewPosition = 0, [0.14, 0.14], "PA"
        ds.WindowCenter, ds.WindowWidth = 2048, 4096
        ds.PixelData = px.tobytes()
        ds.save_as(p, enforce_file_format=True)
        print("wrote", p)

    ct_dir = out / "synthetic_ct"
    ct_dir.mkdir(exist_ok=True)
    study, series = generate_uid(), generate_uid()
    n, size = 40, 128
    zz, yy, xx = np.mgrid[0:n, 0:size, 0:size]
    body = ((xx - 64) / 55) ** 2 + ((yy - 64) / 45) ** 2 < 1
    spleen = ((xx - 95) / 12) ** 2 + ((yy - 70) / 16) ** 2 + ((zz - 20) / 10) ** 2 < 1
    hu = np.where(body, 40, -1000).astype(np.int16) + np.where(spleen, 15, 0).astype(np.int16)
    hu = hu + rng.normal(0, 8, hu.shape).astype(np.int16)
    for k in range(n):
        p = ct_dir / f"slice_{k:03d}.dcm"
        ds = _base(p, CTImageStorage, "CT", study, series, "SYN-CT-001", "M", "061Y")
        ds.Rows = ds.Columns = size
        ds.PixelRepresentation = 1
        ds.RescaleSlope, ds.RescaleIntercept = 1, 0
        ds.PixelSpacing, ds.SliceThickness = [2.5, 2.5], 3.0
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.ImagePositionPatient = [-160, -160, -60 + 3.0 * k]
        ds.InstanceNumber = n - k  # deliberately reversed: ordering must come from geometry
        ds.WindowCenter, ds.WindowWidth = 40, 400
        ds.PixelData = hu[k].astype(np.int16).tobytes()
        ds.save_as(p, enforce_file_format=True)
    print(f"wrote {n} CT slices to", ct_dir)


if __name__ == "__main__":
    main()

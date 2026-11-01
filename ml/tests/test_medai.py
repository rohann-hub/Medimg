"""Fast unit tests for the shared ML package (CPU, no datasets needed).

    python ml/scripts/make_sample_dicoms.py --out samples
    pytest ml/tests -q
"""
from pathlib import Path

import numpy as np
import pytest
import torch

from medai.dicom_io import demographics, load_series, read_dataset, to_display_array
from medai.gradcam import GradCAM
from medai.models import build_classifier, build_unet3d, gradcam_target_layer, load_checkpoint, save_checkpoint
from medai.predict import classify, segment
from medai.transforms import preprocess_2d, xyz_ras_to_zyx_lps, zyx_lps_to_xyz_ras

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
needs_samples = pytest.mark.skipif(not SAMPLES.exists(), reason="run make_sample_dicoms.py first")


@needs_samples
def test_cxr_read_and_demographics():
    ds = read_dataset(SAMPLES / "synthetic_cxr_1.dcm")
    img = to_display_array(ds)
    assert img.shape == (1024, 1024) and img.dtype == np.float32
    assert 0.0 <= img.min() and img.max() <= 1.0
    assert demographics(ds) == {"age": 54, "sex": "F", "view": "PA", "manufacturer": ds.Manufacturer}


@needs_samples
def test_ct_series_sorted_by_geometry_not_instance_number():
    files = sorted((SAMPLES / "synthetic_ct").glob("*.dcm"), reverse=True)  # shuffled order on purpose
    vol = load_series(read_dataset(f) for f in files)
    assert vol.data.shape == (40, 128, 128)
    assert vol.spacing == (3.0, 2.5, 2.5)
    # synthetic spleen centred on slice 20 → brightest mean HU near the middle
    profile = vol.data[:, 60:80, 85:105].mean(axis=(1, 2))
    assert abs(int(np.argmax(profile)) - 20) <= 3


def test_monochrome1_is_inverted():
    from pydicom.dataset import Dataset
    ds = Dataset()
    ds.Rows = ds.Columns = 4
    ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation, ds.SamplesPerPixel = 16, 12, 11, 0, 1
    ds.PhotometricInterpretation = "MONOCHROME1"
    ds.file_meta = __import__("pydicom").dataset.FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = __import__("pydicom").uid.ExplicitVRLittleEndian
    arr = np.arange(16, dtype=np.uint16).reshape(4, 4) * 100
    ds.PixelData = arr.tobytes()
    out = to_display_array(ds)
    assert out[0, 0] > out[-1, -1]  # low raw value must display bright


def test_preprocess_letterbox_shape():
    t = preprocess_2d(np.random.rand(300, 500).astype(np.float32), 320)
    assert t.shape == (3, 320, 320)


def test_orientation_roundtrip():
    v = np.random.rand(5, 6, 7)
    assert np.array_equal(xyz_ras_to_zyx_lps(zyx_lps_to_xyz_ras(v)), v)
    assert zyx_lps_to_xyz_ras(v).shape == (7, 6, 5)


@pytest.mark.parametrize("arch", ["densenet121", "efficientnet_b0"])
def test_gradcam_shape_and_range(arch):
    m = build_classifier(arch, 1, pretrained=False).eval()
    cam, logits = GradCAM(m, gradcam_target_layer(m, arch))(torch.randn(1, 3, 224, 224))
    assert cam.shape == (224, 224) and logits.shape == (1, 1)
    assert cam.min() >= 0 and cam.max() <= 1.0001


def test_checkpoint_roundtrip_and_classify(tmp_path):
    m = build_classifier("densenet121", 1, pretrained=False)
    meta = {"task": "classification", "arch": "densenet121", "labels": ["Lung Opacity"], "image_size": 224,
            "threshold": 0.5, "model_version": "test"}
    save_checkpoint(tmp_path / "c.pt", m, meta)
    m2, meta2 = load_checkpoint(tmp_path / "c.pt")
    res = classify(m2, meta2, np.random.rand(200, 260).astype(np.float32))
    assert set(res.probabilities) == {"Lung Opacity"}
    assert res.cam.shape[0] <= 224 and res.cam.shape[1] == 224  # letterbox padding cropped away


def test_segment_returns_mask_in_original_geometry():
    torch.manual_seed(0)
    m = build_unet3d(2).eval()
    meta = {"labels": ["background", "spleen"], "roi_size": [32, 32, 32]}
    vol = np.random.normal(40, 20, (12, 40, 48)).astype(np.float32)
    res = segment(m, meta, vol, (3.0, 2.0, 2.0))
    assert res.mask.shape == vol.shape and res.mask.dtype == np.uint8

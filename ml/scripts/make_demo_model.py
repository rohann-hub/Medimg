"""Write an UNTRAINED placeholder checkpoint so the full app runs before you have trained anything.

    python ml/scripts/make_demo_model.py            # → models/classifier.pt (random head)

Its predictions are meaningless. The model_version starts with "DEMO-UNTRAINED" and the
viewer shows a red banner while it is loaded. Replace it with a real trained model.
"""
from __future__ import annotations

import argparse

import torch

from medai import CLASSIFIER_LABELS, SEG_LABELS
from medai.models import build_classifier, build_unet3d, save_checkpoint


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="models/classifier.pt")
    ap.add_argument("--arch", default="densenet121")
    ap.add_argument("--imagenet", action="store_true", help="start from ImageNet weights (downloads ~30 MB)")
    ap.add_argument("--seg-out", default="", help="also write an untrained 3D U-Net here")
    a = ap.parse_args()
    torch.manual_seed(0)
    m = build_classifier(a.arch, num_classes=len(CLASSIFIER_LABELS), pretrained=a.imagenet)
    save_checkpoint(a.out, m, {"task": "classification", "arch": a.arch, "labels": CLASSIFIER_LABELS,
                               "image_size": 320, "threshold": 0.5, "model_version": f"DEMO-UNTRAINED-{a.arch}",
                               "trained_on": "nothing — placeholder"})
    print("wrote", a.out)
    if a.seg_out:
        save_checkpoint(a.seg_out, build_unet3d(len(SEG_LABELS)), {
            "task": "segmentation", "arch": "monai_unet3d", "labels": SEG_LABELS, "roi_size": [96, 96, 96],
            "model_version": "DEMO-UNTRAINED-unet3d", "trained_on": "nothing — placeholder"})
        print("wrote", a.seg_out)


if __name__ == "__main__":
    main()

"""Step 3b: 3D U-Net spleen segmentation on CT with MONAI (Medical Segmentation Decathlon Task09).

    python ml/scripts/train_segmentation.py              # downloads Task09_Spleen on first run (~1.5 GB)

Needs a GPU in practice (Colab T4 / Kaggle P100 is enough: ~1-2 h for 300 epochs).
Outputs models/segmentation.pt and metrics/train_seg.json.

Follows the canonical MONAI spleen tutorial so results are comparable
(expect validation Dice ≈ 0.93-0.95).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch
import yaml
from monai.apps import DecathlonDataset
from monai.data import DataLoader, decollate_batch
from monai.inferers import sliding_window_inference
from monai.losses import DiceLoss
from monai.metrics import DiceMetric
from monai.transforms import (
    AsDiscrete, Compose, CropForegroundd, EnsureChannelFirstd, LoadImaged, Orientationd,
    RandCropByPosNegLabeld, RandFlipd, RandRotate90d, RandShiftIntensityd, ScaleIntensityRanged, Spacingd,
)
from monai.utils import set_determinism

from medai import SEG_LABELS
from medai.models import build_unet3d, save_checkpoint
from medai.transforms import CT_WINDOW, SEG_SPACING_XYZ


def transforms(roi, train: bool):
    base = [
        LoadImaged(keys=["image", "label"]),
        EnsureChannelFirstd(keys=["image", "label"]),
        Orientationd(keys=["image", "label"], axcodes="RAS"),
        Spacingd(keys=["image", "label"], pixdim=SEG_SPACING_XYZ, mode=("bilinear", "nearest")),
        ScaleIntensityRanged(keys=["image"], a_min=CT_WINDOW[0], a_max=CT_WINDOW[1], b_min=0.0, b_max=1.0, clip=True),
        CropForegroundd(keys=["image", "label"], source_key="image"),
    ]
    if train:
        base += [
            RandCropByPosNegLabeld(keys=["image", "label"], label_key="label", spatial_size=roi, pos=1, neg=1,
                                   num_samples=4, image_key="image", image_threshold=0),
            RandFlipd(keys=["image", "label"], prob=0.2, spatial_axis=0),
            RandRotate90d(keys=["image", "label"], prob=0.2, max_k=3),
            RandShiftIntensityd(keys=["image"], offsets=0.1, prob=0.5),
        ]
    return Compose(base)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    args = ap.parse_args()
    p = yaml.safe_load(open(args.params))["train_seg"]
    set_determinism(p["seed"])
    roi = tuple(p["roi_size"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    Path(p["data_dir"]).mkdir(parents=True, exist_ok=True)

    common = dict(root_dir=p["data_dir"], task="Task09_Spleen", download=True, seed=p["seed"],
                  cache_rate=p["cache_rate"], num_workers=p["num_workers"])
    train_ds = DecathlonDataset(section="training", transform=transforms(roi, True), **common)
    val_ds = DecathlonDataset(section="validation", transform=transforms(roi, False), **common)
    train_dl = DataLoader(train_ds, batch_size=2, shuffle=True, num_workers=p["num_workers"])
    val_dl = DataLoader(val_ds, batch_size=1, num_workers=p["num_workers"])

    model = build_unet3d(len(SEG_LABELS)).to(device)
    loss_fn = DiceLoss(to_onehot_y=True, softmax=True)
    opt = torch.optim.Adam(model.parameters(), p["lr"])
    dice = DiceMetric(include_background=False, reduction="mean")
    post_pred, post_lbl = AsDiscrete(argmax=True, to_onehot=2), AsDiscrete(to_onehot=2)

    best, history = -1.0, []
    for epoch in range(p["max_epochs"]):
        model.train()
        ep_loss = 0.0
        for batch in train_dl:
            x, y = batch["image"].to(device), batch["label"].to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            ep_loss += loss.item()
        ep_loss /= len(train_dl)
        rec = {"epoch": epoch + 1, "loss": round(ep_loss, 4)}
        if (epoch + 1) % p["val_interval"] == 0:
            model.eval()
            with torch.no_grad():
                for batch in val_dl:
                    x, y = batch["image"].to(device), batch["label"].to(device)
                    out = sliding_window_inference(x, roi, 4, model)
                    dice(y_pred=[post_pred(i) for i in decollate_batch(out)], y=[post_lbl(i) for i in decollate_batch(y)])
            score = float(dice.aggregate().item())
            dice.reset()
            rec["val_dice"] = round(score, 4)
            if score > best:
                best = score
                save_checkpoint("models/segmentation.pt", model, {
                    "task": "segmentation", "arch": "monai_unet3d", "labels": SEG_LABELS, "roi_size": list(roi),
                    "model_version": f"unet3d-spleen-{datetime.now(timezone.utc):%Y%m%d%H%M}",
                    "trained_on": "Medical Segmentation Decathlon Task09_Spleen", "val_dice": score,
                    "spacing_xyz": list(SEG_SPACING_XYZ), "ct_window": list(CT_WINDOW),
                })
        history.append(rec)
        print(rec)
    Path("metrics").mkdir(exist_ok=True)
    json.dump({"best_val_dice": best, "history": history}, open("metrics/train_seg.json", "w"), indent=2)


if __name__ == "__main__":
    main()

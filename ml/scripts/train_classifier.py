"""Step 3: transfer-learning classifier (DenseNet121 / EfficientNet) on RSNA chest X-rays.

    python ml/scripts/train_classifier.py            # uses params.yaml
    dvc repro train_cls                              # same, but tracked

Outputs models/classifier.pt (weights + metadata) and metrics/train_cls.json.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from medai import CLASSIFIER_LABELS
from medai.models import build_classifier, save_checkpoint
from medai.transforms import preprocess_2d, train_augment_2d


class CxrDataset(Dataset):
    def __init__(self, df: pd.DataFrame, img_dir: Path, size: int, augment: bool):
        self.df, self.img_dir, self.size = df.reset_index(drop=True), img_dir, size
        self.aug = train_augment_2d(size) if augment else None

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, i):
        r = self.df.iloc[i]
        img = np.asarray(Image.open(self.img_dir / f"{r.patientId}.png").convert("L"), dtype=np.float32) / 255.0
        if self.aug is not None:
            t = torch.from_numpy(img)[None]
            img = self.aug(t)[0].clamp(0, 1).numpy()
        return preprocess_2d(img, self.size), torch.tensor([float(r.label)])


def seed_all(s: int) -> None:
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)


@torch.no_grad()
def predict(model, loader, device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    ys, ps = [], []
    for x, y in loader:
        ps.append(torch.sigmoid(model(x.to(device))).cpu().numpy()[:, 0])
        ys.append(y.numpy()[:, 0])
    return np.concatenate(ys), np.concatenate(ps)


def threshold_for_sensitivity(y: np.ndarray, p: np.ndarray, target: float) -> float:
    fpr, tpr, thr = roc_curve(y, p)
    ok = np.where(tpr >= target)[0]
    return float(thr[ok[0]]) if len(ok) else 0.5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    args = ap.parse_args()
    params = yaml.safe_load(open(args.params))
    p, data_dir = params["train_cls"], Path(params["prepare"]["out_dir"])
    seed_all(p["seed"])
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print("device:", device)

    df = pd.read_csv(data_dir / "metadata.csv")
    tr, va = df[df.split == "train"], df[df.split == "val"]
    mk = lambda d, aug, sh: DataLoader(CxrDataset(d, data_dir / "images", p["image_size"], aug),
                                       batch_size=p["batch_size"], shuffle=sh, num_workers=p["num_workers"],
                                       pin_memory=device == "cuda")
    train_dl, val_dl = mk(tr, True, True), mk(va, False, False)

    model = build_classifier(p["arch"], num_classes=1, pretrained=p.get("pretrained", True)).to(device)
    pos_weight = torch.tensor([(tr.label == 0).sum() / max(1, (tr.label == 1).sum())], device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # counter class imbalance (~22% positive)
    opt = torch.optim.AdamW(model.parameters(), lr=p["lr"], weight_decay=p["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=p["epochs"])
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")
    head = model.classifier if p["arch"] == "densenet121" else model.classifier[-1]

    best_auc, bad_epochs, history = -1.0, 0, []
    ckpt_path = Path("models/classifier.pt")
    for epoch in range(p["epochs"]):
        frozen = epoch < p["freeze_backbone_epochs"]
        for prm in model.parameters():
            prm.requires_grad = not frozen
        for prm in head.parameters():
            prm.requires_grad = True
        model.train()
        t0, running = time.time(), 0.0
        for x, y in tqdm(train_dl, desc=f"epoch {epoch + 1}/{p['epochs']}{' (head only)' if frozen else ''}"):
            x, y = x.to(device), y.to(device)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", enabled=device == "cuda"):
                loss = loss_fn(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            running += loss.item() * len(x)
        sched.step()
        yv, pv = predict(model, val_dl, device)
        auc = float(roc_auc_score(yv, pv))
        history.append({"epoch": epoch + 1, "train_loss": running / len(tr), "val_auroc": auc, "sec": time.time() - t0})
        print(history[-1])
        if auc > best_auc:
            best_auc, bad_epochs = auc, 0
            thr = threshold_for_sensitivity(yv, pv, p["target_sensitivity"])
            version = f"{p['arch']}-rsna-{datetime.now(timezone.utc):%Y%m%d%H%M}"
            save_checkpoint(ckpt_path, model, {
                "task": "classification", "arch": p["arch"], "labels": CLASSIFIER_LABELS,
                "image_size": p["image_size"], "threshold": thr, "model_version": version,
                "trained_on": "RSNA Pneumonia Detection Challenge (stage 2 train)",
                "val_auroc": auc, "epoch": epoch + 1, "params": p,
            })
        else:
            bad_epochs += 1
            if bad_epochs >= p["early_stop_patience"]:
                print("early stopping")
                break

    Path("metrics").mkdir(exist_ok=True)
    json.dump({"best_val_auroc": best_auc, "history": history}, open("metrics/train_cls.json", "w"), indent=2)
    print(f"best val AUROC {best_auc:.4f} → {ckpt_path}")


if __name__ == "__main__":
    main()

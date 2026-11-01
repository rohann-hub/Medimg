"""Evaluate on the held-out TEST split. Run once, at the end — never tune on test.

Reports (metrics/eval_cls.json + reports/eval_cls.md + reports/roc.png):
  * AUROC with 95% bootstrap CI
  * sensitivity / specificity / PPV / NPV at the threshold chosen on VAL
  * expected calibration error (are 0.8 predictions right 80% of the time?)
  * subgroup AUROC + sensitivity by sex, age band and view (AP vs PA) → bias analysis
  * Grad-CAM "pointing game": % of positive images whose heatmap peak falls inside
    a radiologist-drawn opacity box — a quantitative check on the explanations
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader

from medai.models import load_checkpoint
from medai.predict import classify

import sys
sys.path.insert(0, str(Path(__file__).parent))
from train_classifier import CxrDataset, predict  # noqa: E402


def bootstrap_auc(y, p, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    aucs = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) == 2:
            aucs.append(roc_auc_score(y[idx], p[idx]))
    return float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.any():
            total += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(total)


def operating_point(y, p, thr):
    pred = p >= thr
    tp, fn = int((pred & (y == 1)).sum()), int((~pred & (y == 1)).sum())
    tn, fp = int((~pred & (y == 0)).sum()), int((pred & (y == 0)).sum())
    div = lambda a, b: round(a / b, 4) if b else None
    return {"threshold": round(thr, 4), "sensitivity": div(tp, tp + fn), "specificity": div(tn, tn + fp),
            "ppv": div(tp, tp + fp), "npv": div(tn, tn + fn), "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    ap.add_argument("--pointing-n", type=int, default=300, help="positives to run Grad-CAM on")
    args = ap.parse_args()
    params = yaml.safe_load(open(args.params))
    data_dir = Path(params["prepare"]["out_dir"])
    model, meta = load_checkpoint("models/classifier.pt")
    df = pd.read_csv(data_dir / "metadata.csv")
    te = df[df.split == "test"].reset_index(drop=True)
    dl = DataLoader(CxrDataset(te, data_dir / "images", meta["image_size"], False), batch_size=32, num_workers=2)
    y, p = predict(model, dl, "cpu")
    te["prob"] = p

    lo, hi = bootstrap_auc(y, p)
    out = {"model_version": meta["model_version"], "n_test": len(te), "prevalence": float(y.mean()),
           "auroc": float(roc_auc_score(y, p)), "auroc_95ci": [lo, hi], "ece": ece(y, p),
           "operating_point": operating_point(y, p, meta["threshold"]), "subgroups": {}}

    te["age_band"] = pd.cut(te.age, [0, 18, 40, 60, 200], labels=["<18", "18-39", "40-59", "60+"], right=False)
    for col in ["sex", "age_band", "view"]:
        res = {}
        for val, g in te.groupby(col, observed=True):
            if g.label.nunique() < 2 or len(g) < 30:
                continue
            res[str(val)] = {"n": len(g), "prevalence": round(g.label.mean(), 3),
                             "auroc": round(roc_auc_score(g.label, g.prob), 4),
                             **{k: v for k, v in operating_point(g.label.values, g.prob.values, meta["threshold"]).items()
                                if k in ("sensitivity", "specificity")}}
        out["subgroups"][col] = res

    # Pointing game
    pos = te[te.label == 1].head(args.pointing_n)
    hits = 0
    for r in pos.itertuples():
        img = np.asarray(Image.open(data_dir / "images" / f"{r.patientId}.png").convert("L"), np.float32) / 255
        cam = classify(model, meta, img).cam
        yy, xx = np.unravel_index(int(cam.argmax()), cam.shape)
        sy, sx = r.orig_h / cam.shape[0], r.orig_w / cam.shape[1]
        py, px = yy * sy, xx * sx
        hits += any(b["x"] <= px <= b["x"] + b["width"] and b["y"] <= py <= b["y"] + b["height"]
                    for b in json.loads(r.boxes_json))
    out["gradcam_pointing_game"] = {"n": len(pos), "hit_rate": round(hits / max(1, len(pos)), 4)}

    Path("metrics").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    json.dump(out, open("metrics/eval_cls.json", "w"), indent=2)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fpr, tpr, _ = roc_curve(y, p)
    plt.figure(figsize=(4.5, 4.5))
    plt.plot(fpr, tpr, label=f"AUROC {out['auroc']:.3f}")
    plt.plot([0, 1], [0, 1], "--", color="grey")
    op = out["operating_point"]
    plt.scatter([1 - op["specificity"]], [op["sensitivity"]], color="red", zorder=3, label="operating point")
    plt.xlabel("1 - specificity"); plt.ylabel("sensitivity"); plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig("reports/roc.png", dpi=150)

    lines = [f"# Test-set evaluation — {meta['model_version']}", "",
             f"- N = {out['n_test']}, prevalence = {out['prevalence']:.1%}",
             f"- AUROC = {out['auroc']:.3f} (95% CI {lo:.3f}–{hi:.3f})",
             f"- ECE = {out['ece']:.3f}",
             f"- At threshold {op['threshold']}: sensitivity {op['sensitivity']}, specificity {op['specificity']}, "
             f"PPV {op['ppv']}, NPV {op['npv']}",
             f"- Grad-CAM pointing game: {out['gradcam_pointing_game']['hit_rate']:.1%} "
             f"of {out['gradcam_pointing_game']['n']} positives", "", "## Subgroups", ""]
    for col, res in out["subgroups"].items():
        lines += [f"### {col}", "", "| group | n | prevalence | AUROC | sensitivity | specificity |", "|---|---|---|---|---|---|"]
        lines += [f"| {k} | {v['n']} | {v['prevalence']} | {v['auroc']} | {v['sensitivity']} | {v['specificity']} |"
                  for k, v in res.items()]
        lines.append("")
    Path("reports/eval_cls.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

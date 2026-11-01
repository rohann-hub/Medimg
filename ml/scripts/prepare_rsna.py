"""Step 1-2: RSNA Pneumonia DICOMs → normalized PNGs + metadata.csv with a patient-level split.

Expected input (Kaggle `rsna-pneumonia-detection-challenge`):
    data/raw/rsna/stage_2_train_labels.csv
    data/raw/rsna/stage_2_train_images/*.dcm

Output:
    data/processed/rsna/images/<patientId>.png
    data/processed/rsna/metadata.csv   (patientId, label, split, sex, age, view, boxes_json, orig_h, orig_w)

Why patient-level split: one patient can have several images in other datasets;
if the same patient lands in train and test you measure memorisation, not generalisation.
RSNA happens to be one image per patient, but the code does it right anyway.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from PIL import Image
from sklearn.model_selection import train_test_split
from tqdm import tqdm

from medai.dicom_io import demographics, read_dataset, to_display_array


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    args = ap.parse_args()
    p = yaml.safe_load(open(args.params))["prepare"]
    raw, out = Path(p["raw_dir"]), Path(p["out_dir"])
    (out / "images").mkdir(parents=True, exist_ok=True)

    labels = pd.read_csv(raw / "stage_2_train_labels.csv")
    boxes = (
        labels[labels.Target == 1]
        .groupby("patientId")[["x", "y", "width", "height"]]
        .apply(lambda g: g.to_dict("records"))
        .to_dict()
    )
    per_patient = labels.groupby("patientId").Target.max().reset_index().rename(columns={"Target": "label"})
    if p["limit"]:
        per_patient = per_patient.groupby("label", group_keys=False).apply(
            lambda g: g.sample(min(len(g), p["limit"] // 2), random_state=p["seed"])
        )

    rows = []
    for pid, label in tqdm(per_patient[["patientId", "label"]].itertuples(index=False), total=len(per_patient)):
        dcm = raw / "stage_2_train_images" / f"{pid}.dcm"
        if not dcm.exists():
            continue
        ds = read_dataset(dcm)
        img = to_display_array(ds)
        h, w = img.shape
        Image.fromarray((img * 255).astype(np.uint8)).resize((p["image_size"],) * 2, Image.BILINEAR).save(
            out / "images" / f"{pid}.png"
        )
        rows.append({"patientId": pid, "label": int(label), **demographics(ds),
                     "boxes_json": json.dumps(boxes.get(pid, [])), "orig_h": h, "orig_w": w})

    df = pd.DataFrame(rows)
    trval, test = train_test_split(df, test_size=p["test_frac"], stratify=df.label, random_state=p["seed"])
    train, val = train_test_split(trval, test_size=p["val_frac"] / (1 - p["test_frac"]), stratify=trval.label,
                                  random_state=p["seed"])
    df["split"] = "train"
    df.loc[val.index, "split"] = "val"
    df.loc[test.index, "split"] = "test"
    df.to_csv(out / "metadata.csv", index=False)
    print(df.groupby(["split", "label"]).size().unstack())
    # Show the class/demographic mix — this goes straight into the model card.
    print(df.groupby("split")[["sex", "view"]].value_counts().unstack(fill_value=0))


if __name__ == "__main__":
    main()

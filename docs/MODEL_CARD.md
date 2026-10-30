# Model Card — fill the `TODO` numbers from `metrics/eval_cls.json` and `metrics/train_seg.json`

> Educational / research prototype. Not clinically validated. Not for diagnosis.

## 1. Chest X-ray opacity classifier

| | |
|---|---|
| Task | Binary: *Lung Opacity* (pneumonia-like) vs not, on frontal chest radiographs |
| Architecture | DenseNet121 (ImageNet init), 1 sigmoid output, 320×320 letterboxed input |
| Training data | RSNA Pneumonia Detection Challenge (stage 2 train, ~26.7k images, ~22% positive) |
| Split | 70/15/15 stratified, patient-level, seed 42 |
| Loss / optimiser | BCE with `pos_weight`, AdamW, cosine LR, 1 frozen-backbone warm-up epoch, early stopping on val AUROC |
| Operating point | Threshold chosen on **validation** to reach 90% sensitivity |
| Explainability | Grad-CAM on `features.denseblock4` |
| Intended use | Teaching demo of a human-in-the-loop decision-support workflow |
| Out of scope | Diagnosis; paediatric images; lateral views; CT/MRI; any image source not seen in training |

### Results (test split, never used for tuning)

| Metric | Value |
|---|---|
| AUROC (95% bootstrap CI) | TODO (TODO–TODO) |
| Sensitivity / specificity @ threshold | TODO / TODO |
| PPV / NPV | TODO / TODO |
| Expected calibration error | TODO |
| Grad-CAM pointing game (peak inside radiologist box) | TODO % |

### Subgroup performance — copy the tables from `reports/eval_cls.md`

Report AUROC and sensitivity by **sex**, **age band** and **view position (AP vs PA)**. A gap of
> 0.05 AUROC or > 10 points sensitivity is worth a paragraph.

### Known dataset limitations and biases

- **Source:** images originate from the NIH ChestX-ray14 collection (one US hospital system).
  Scanner types, patient mix and disease prevalence differ from Indian hospitals; expect
  performance to drop on external data (domain shift).
- **Labels:** RSNA boxes were drawn by radiologists, but "Lung Opacity" is broader than
  pneumonia (also atelectasis, oedema, masses). Inter-reader agreement is moderate.
- **AP vs PA confounding:** AP films are taken on sicker, often bed-bound patients and have a
  higher positive rate. A model can learn "AP film → positive" — check the view subgroup table
  and the heatmaps for attention on markers, tubes, or image borders.
- **Demographics:** only age and sex are recorded; race/ethnicity and socioeconomic data are
  absent, so fairness across those groups cannot be measured.
- **Prevalence:** ~22% positive in the dataset ≠ real-world screening prevalence; PPV will be
  lower in practice.
- **Grad-CAM:** coarse (≈10×10 grid upsampled), shows correlation not causation, and can look
  plausible even when the model is wrong.

## 2. CT spleen segmentation

| | |
|---|---|
| Task | Voxel-wise spleen segmentation on portal-venous abdominal CT |
| Architecture | MONAI 3D U-Net, channels 16-32-64-128-256, 2 residual units, batch norm |
| Data | Medical Segmentation Decathlon Task09 (41 labelled CTs; MONAI's 80/20 split) |
| Preprocessing | RAS orientation, 1.5×1.5×2.0 mm spacing, HU window [-57, 164] → [0,1] |
| Inference | Sliding window 96³, overlap 0.25 |
| Validation Dice | TODO |

Limitations: very small training set (41 scans, one institution); assumes standard axial
orientation in DICOM; no lesion detection — volume (mL) is reported for teaching only.

## 3. Ethics, privacy, and governance

- Public datasets used under their licences/terms (Kaggle competition rules, CC-BY-SA 4.0 for MSD).
- No real patient data enters the demo; synthetic DICOMs are generated for testing.
- Patient IDs are pseudonymised (salted SHA-256) in the application DB.
- Every inference, view and decision is logged with user, time, model version and weights hash.
- A real deployment in India would need: CDSCO software-as-medical-device classification,
  DPDP Act 2023 compliance, institutional ethics committee approval, and prospective clinical validation.

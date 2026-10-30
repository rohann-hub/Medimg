# 8-week plan, report outline, viva prep

## Plan

| Week | Deliverable | Done when |
|---|---|---|
| 1 | Environment, `docker compose up` with demo model, DICOM primer read, dataset access (Kaggle RSNA, MSD) | You can upload a sample and see a heatmap |
| 2 | `prepare` stage on full RSNA; EDA notebook (class balance, sex/age/view mix, image sizes) | `data/processed/rsna/metadata.csv` tracked by DVC |
| 3 | Classifier training on Kaggle GPU; first `metrics/train_cls.json` | Val AUROC ≥ 0.83 |
| 4 | Experiments: DenseNet121 vs EfficientNet-B0, 224 vs 320 px, with/without augmentation (`dvc metrics diff`) | Comparison table |
| 5 | Test evaluation: CI, calibration, subgroups, pointing game; heatmap error analysis (20 FP + 20 FN reviewed) | `reports/eval_cls.md` |
| 6 | 3D U-Net spleen segmentation; Dice; CT flow in viewer | Val Dice ≥ 0.90 |
| 7 | Hardening: real model in Docker, tests green, model card filled, screenshots, demo video | Fresh clone → working demo in < 15 min |
| 8 | Report + slides + viva rehearsal | — |

## Report outline (≈ 40–60 pages)

1. Introduction — problem, why decision support (not diagnosis), objectives
2. Literature review — CheXNet, DenseNet, EfficientNet, U-Net/3D U-Net, Grad-CAM and its critiques, MONAI, shortcut learning (Zech 2018; DeGrave 2021)
3. Data — DICOM, datasets, preprocessing, splits, DVC
4. Methods — transfer learning, loss/imbalance, threshold selection, Grad-CAM maths, segmentation pipeline
5. System design — architecture diagram, Orthanc integration, change feed, DB schema, audit chain, security
6. Results — training curves, experiment table, test metrics with CI, ROC, calibration, subgroup table, pointing game, Dice
7. Explainability analysis — good and misleading heatmaps, what the model attends to
8. Limitations, bias, ethics, regulation (CDSCO SaMD, DPDP Act 2023)
9. Conclusion & future work — multi-label CheXpert, OHIF viewer via DICOMweb, active learning from rejections, external validation
10. Appendices — API, model card, test report

## Viva questions you should be able to answer

- Why patient-level split? What leakage did you check for?
- Why AUROC and not accuracy? What happens to PPV at 5% prevalence?
- How was the threshold chosen, and why on validation not test?
- Explain Grad-CAM in one equation. When does it mislead?
- What does the pointing-game number tell you, and what doesn't it?
- How do you know which model produced a prediction six months ago?
- What happens if Orthanc receives half a CT series? (StableStudy / StableAge)
- How would you detect that someone edited the audit log?
- What would change for real deployment in an Indian hospital?
- Your model's AP-view sensitivity differs from PA — why might that be?

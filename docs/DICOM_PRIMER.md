# DICOM in 10 minutes (Step 1 of the brief)

DICOM is both a **file format** and a **network protocol** for medical images.

## The hierarchy

```
Patient ── Study (one visit/exam, StudyInstanceUID)
             └── Series (one acquisition, SeriesInstanceUID, one Modality)
                   └── Instance (one image/slice file, SOPInstanceUID)
```
A chest X-ray study is usually 1–2 instances. A CT study is one or more series of 100–1000 slices,
**one file per slice**.

## Tags you will actually use

| Tag | Keyword | Why it matters |
|---|---|---|
| (0008,0060) | Modality | CR/DX = X-ray, CT, MR — routes the study to the right model |
| (0028,0004) | PhotometricInterpretation | MONOCHROME1 = inverted greyscale, must flip |
| (0028,1052/1053) | RescaleIntercept / Slope | raw → real units (Hounsfield Units for CT) |
| (0028,1050/1051) | WindowCenter / Width | how the radiologist expects it displayed |
| (0028,0030) | PixelSpacing | mm per pixel — needed for volumes (mL) and resampling |
| (0020,0032) | ImagePositionPatient | 3D position of the slice — **sort slices by this** |
| (0020,0037) | ImageOrientationPatient | slice direction cosines |
| (0018,5101) | ViewPosition | AP vs PA — a classic confounder |
| (0010,0020/0010) | PatientID / PatientName | identifiers — must be protected |

Try it:
```python
import pydicom
ds = pydicom.dcmread("samples/synthetic_cxr_1.dcm")
print(ds)                       # every tag
print(ds.Modality, ds.pixel_array.shape, ds.pixel_array.dtype)
```

## Hounsfield Units & windowing (CT)

HU: air −1000, fat ≈ −100, water 0, soft tissue 20–80, bone 400–1000+. Screens show 256
grey levels, so you choose a **window**: soft tissue W400/L40 → −160…240 HU. The segmentation
model uses an abdominal window −57…164 HU.

## Coordinate systems

DICOM uses **LPS** (+x → patient Left, +y → Posterior, +z → Superior). NIfTI/MONAI training data
is reoriented to **RAS**. `medai/transforms.py` converts between them so the model sees the same
anatomy layout at training and inference — a real bug class in medical-imaging projects.

## Networking

Scanners send images to PACS with **C-STORE** (port 104/4242). Web apps use **DICOMweb**
(QIDO-RS search, WADO-RS retrieve, STOW-RS store). Orthanc speaks both plus its own REST API,
which this project uses (`/instances`, `/studies/{id}/series`, `/changes`).

## De-identification

Before sharing images, remove/replace PHI tags (DICOM PS3.15 Annex E). Also check for
**burned-in text** in pixels (names on old X-rays). Tools: `pydicom` + `deid`, Orthanc's
`/anonymize` endpoint, or RSNA's CTP anonymizer.

## Datasets

| Dataset | Format | Note |
|---|---|---|
| RSNA Pneumonia | DICOM | used here; has boxes → enables Grad-CAM pointing game |
| NIH ChestX-ray14 | PNG | 14 labels, 112k images, NLP-mined labels |
| CheXpert | JPG | 224k images, uncertainty labels; registration required |
| MIMIC-CXR | DICOM | PhysioNet credentialing + CITI training required (takes weeks) |
| MSD | NIfTI | used here (Task09 Spleen); 10 segmentation tasks |
| LIDC-IDRI | DICOM | lung nodules CT, 4-reader annotations |
| BraTS | NIfTI | brain tumour MRI, registration required |

# AI-Assisted Medical Imaging & Diagnosis System

Capstone / industry project: doctors upload X-ray, CT or MRI studies; the system stores them in a
DICOM server (Orthanc), runs AI automatically, shows **Grad-CAM heatmaps** (X-ray) or **3D
segmentation masks** (CT), and records every **approve / reject** decision in a tamper-evident
audit trail.

> **Educational / research use only.** Not a medical device. AI output is decision support and
> must be reviewed by a qualified clinician.

```
                 ┌──────────── React viewer (frontend/) ─────────────┐
 Doctor ───────► │ worklist · scan + heatmap/mask · approve/reject   │
                 └──────────────────────┬────────────────────────────┘
                                        │ /api (OAuth2 password flow, JWT bearer)
                 ┌──────────────────────▼────────────────────────────┐
 .dcm / .zip ──► │ FastAPI backend (backend/app)                     │
                 │  upload ──► Orthanc REST                          │
                 │  worker  ◄── Orthanc /changes  (StableStudy)      │
                 │  inference: DenseNet121 + Grad-CAM | MONAI U-Net  │
                 │  SQLite: studies, predictions, decisions, audit   │
                 └──────────────────────┬────────────────────────────┘
                                        │
 Modality / PACS ── DICOM C-STORE ─► Orthanc (port 4242)   ◄── also picked up automatically
```

## Brief → where it lives

| Brief step | Implementation |
|---|---|
| 1. Dataset & DICOM | `docs/DICOM_PRIMER.md`, `ml/medai/dicom_io.py` (rescale, VOI LUT, MONOCHROME1, geometry-sorted series) |
| 2. Preprocessing, augmentation, DVC | `ml/scripts/prepare_rsna.py`, `ml/medai/transforms.py`, `dvc.yaml`, `params.yaml` |
| 3. Transfer-learning classifier | `ml/scripts/train_classifier.py` (DenseNet121 / EfficientNet, PyTorch) |
| 3. 3D U-Net segmentation (MONAI) | `ml/scripts/train_segmentation.py` (MSD Task09 Spleen CT) |
| 4. Grad-CAM + confidence | `ml/medai/gradcam.py` (from scratch), `ml/medai/predict.py`, pointing-game metric in `evaluate_classifier.py` |
| 5. Orthanc + auto inference | `backend/app/worker.py` (change feed), `backend/app/inference.py`, `backend/app/orthanc.py` |
| 6. React viewer | `frontend/src/components/*` — overlay opacity, zoom/pan, brightness/contrast, CT slice scroll, approve/reject, audit |
| 7. Docker, docs, disclaimer, tests | `docker-compose.yml`, `docs/MODEL_CARD.md`, disclaimer in UI + API, `ml/tests`, `backend/tests` |

## Quick start (Windows, Docker Desktop) — runs before you train anything

```powershell
git clone <your repo> medimg-capstone; cd medimg-capstone
copy .env.example .env                       # then edit passwords/secrets

python -m venv .venv; .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -e ".\ml[train]"

python ml\scripts\make_demo_model.py --out models\classifier.pt --seg-out models\segmentation.pt
python ml\scripts\make_sample_dicoms.py --out samples

docker compose up --build
```

Open http://localhost:8080, sign in (`dr.demo` / `demo123` by default), drag
`samples\synthetic_cxr_1.dcm` onto **Upload DICOM**. About 5–10 s later (Orthanc's
`StableAge` + inference) the study shows **Needs review** with a heatmap. For CT, zip the
`samples\synthetic_ct` folder and upload the zip.

A red banner stays up while the **untrained placeholder** model is loaded — its outputs are random.
Train a real model (below), drop it into `models\`, then restart the backend
(or call `POST /api/admin/reload-models` as admin).

### Without Docker (development)

```powershell
# 1. Orthanc: install from https://www.orthanc-server.com/download-windows.php (listens on 8042)
# 2. Backend (from the project root, venv active)
pip install -e .\ml                                  # the shared medai package
pip install -r backend\requirements.txt
cd backend; uvicorn app.main:app --reload            # uses ..\models\*.pt by default
# 3. Frontend (Node 20+)
cd frontend; npm install; npm run dev                # http://localhost:5173, /api proxied to :8000
```

## Training (needs a GPU — use Kaggle or Colab free tier)

1. **Data.** Download the [RSNA Pneumonia Detection Challenge](https://www.kaggle.com/c/rsna-pneumonia-detection-challenge)
   into `data/raw/rsna/` (accept the competition rules first). Easiest: run training *inside a
   Kaggle notebook* with the competition attached — no 4 GB download.
2. **Pipeline.**
   ```bash
   dvc init                       # once
   dvc repro                      # prepare → train_cls → evaluate_cls  (+ train_seg)
   dvc metrics show               # AUROC, CI, sensitivity, subgroup table
   ```
   Laptop dry run: set `prepare.limit: 3000` and `train_cls.epochs: 2` in `params.yaml`.
3. **Experiments.** Change e.g. `train_cls.arch: efficientnet_b0`, `dvc repro`, then
   `dvc metrics diff` — that comparison table belongs in your report.
4. **Segmentation.** `python ml/scripts/train_segmentation.py` downloads MSD Task09 Spleen
   (~1.5 GB) and trains the 3D U-Net (≈1–2 h on a T4; expect validation Dice ≈ 0.93).
5. Copy `models/classifier.pt` / `models/segmentation.pt` back to your machine.
   `dvc remote add -d storage <gdrive://… or s3://…>` + `dvc push` versions them properly.

Expected classifier results on RSNA test split (DenseNet121, 320 px, ~12 epochs):
AUROC ≈ 0.85–0.89. If you see > 0.95, look for leakage.

## Tests

```bash
python ml/scripts/make_sample_dicoms.py --out samples
python ml/scripts/make_demo_model.py --out models/classifier.pt --seg-out models/segmentation.pt
pytest ml/tests -q                 # DICOM I/O, orientation, Grad-CAM, checkpoints, segmentation
cd backend && pytest -q            # full upload → worker → inference → decision → audit flow (fake Orthanc)
```
The backend test also proves tampering with any audit row is detected.

## Authentication — OAuth2 password flow + JWT

| | |
|---|---|
| Access token | JWT, HS256, 15 min, `Authorization: Bearer <token>`; claims `sub, username, role, ver, iss, aud, iat, nbf, exp, jti, typ` |
| Refresh token | JWT, 7 days, stored by `jti` in the DB, **rotated on every use**; replaying an old one revokes the whole session family |
| Passwords | bcrypt (cost 12), users table; `USERS` in `.env` only seeds the first start |
| Revocation | disabling a user, resetting or changing a password bumps `token_version` → all their tokens die immediately |
| Brute force | 5 failed logins → 15 min lockout per username (HTTP 429 + `Retry-After`); constant-time check for unknown users |
| Swagger | `/docs` → **Authorize** → enter username + password → every request is sent with the JWT |

Production would swap the local user table for the hospital identity provider via OpenID Connect
(Keycloak, Azure AD) and verify RS256 tokens with the provider's public keys; only `current_user` changes.

## API (full OpenAPI at `/docs`)

| Method | Path | Who |
|---|---|---|
| POST | `/api/auth/token` (OAuth2 form) · `/api/auth/login` (JSON) | anyone |
| POST | `/api/auth/refresh` · `/api/auth/logout` `{refresh_token}` | token holder |
| GET / POST | `/api/me` · `/api/me/password` | signed in |
| GET / POST / PATCH | `/api/users`, `/api/users/{id}` | admin |
| POST | `/api/upload` (`.dcm` or `.zip`) | clinician, admin |
| GET | `/api/studies`, `/api/studies/{id}` | signed in |
| GET | `/api/studies/{id}/image.png` · `heatmap.png` · `slices/{k}.png?layer=image|mask` | signed in |
| POST | `/api/predictions/{id}/decision` `{decision, comment}` — reject requires comment | clinician |
| POST | `/api/studies/{id}/reprocess`, `/api/admin/reload-models` | admin |
| GET | `/api/audit`, `/api/audit/verify`, `/api/stats`, `/api/info`, `/api/health` | signed in / public |

## Design decisions worth defending in the viva

- **Shared `medai` package** for training *and* serving → no train/serve preprocessing skew.
- **Orthanc change feed (`StableStudy`)**, not the upload endpoint, triggers inference → works for
  studies arriving from any modality via C-STORE, and only once the whole series is in.
- **Threshold picked on validation for 90% sensitivity** (screening), stored inside the checkpoint.
- **Model version + SHA-256 of the weights** stored with every prediction → full traceability.
- **Hash-chained audit log**: each event stores the previous event's hash; `/api/audit/verify` detects edits/deletes.
- **Pseudonymised patient reference** (salted hash) in the app DB; raw identifiers stay in Orthanc.
- **Reject requires a comment**; decisions are append-only (changing your mind adds a row, never edits one).
- **Re-running AI supersedes** old predictions instead of deleting them.

## Known limitations (also in `docs/MODEL_CARD.md`)

Grad-CAM is coarse (10×10 at 320 px) and can highlight shortcuts. RSNA labels come from a
single source with known AP/PA and ICU confounding. Synthetic samples only test plumbing.
Auth uses a local user table — production needs the hospital IdP (OIDC/SSO with MFA), HTTPS,
encryption at rest, and a DPDP Act 2023 / HIPAA-style data-protection review.

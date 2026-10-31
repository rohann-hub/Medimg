"""End-to-end API tests with an in-memory fake Orthanc (no Docker needed).

Exercises the real pipeline: upload → Orthanc → change feed → worker → inference →
Grad-CAM / segmentation artifacts → clinician decision → hash-chained audit trail.

    python ml/scripts/make_sample_dicoms.py --out samples
    python ml/scripts/make_demo_model.py --out models/classifier.pt --seg-out models/segmentation.pt
    cd backend && pytest -q
"""
from __future__ import annotations

import hashlib
import io
import os
import sys
import time
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "samples"
pytestmark = pytest.mark.skipif(not (SAMPLES.exists() and (ROOT / "models/classifier.pt").exists()),
                                reason="generate samples + demo models first (see module docstring)")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("srv")
    os.environ.update({
        "DATABASE_URL": f"sqlite:///{tmp}/app.db", "ARTIFACT_DIR": str(tmp / "art"),
        "CLS_MODEL_PATH": str(ROOT / "models/classifier.pt"), "SEG_MODEL_PATH": str(ROOT / "models/segmentation.pt"),
        "POLL_SECONDS": "0.2", "USERS": "dr.a:pw:clinician,admin:pw:admin,dr.b:pw:clinician",
        "JWT_SECRET": "test-secret-that-is-long-enough-for-hs256", "LOGIN_MAX_FAILURES": "3",
    })
    sys.path.insert(0, str(ROOT / "backend"))
    for m in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[m]
    from fastapi.testclient import TestClient
    import app.main as main
    from app.db.db import SessionLocal

    import pydicom

    class FakeOrthanc:
        """Implements the subset of the Orthanc REST API the backend uses, including StableStudy changes."""

        def __init__(self):
            self.instances: dict[str, bytes] = {}
            self.series: dict[str, dict] = {}
            self.studies: dict[str, list[str]] = {}
            self.changes_log: list[dict] = []

        @staticmethod
        def _id(*parts):
            return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]

        def system(self):
            return {"Version": "fake"}

        def upload(self, b):
            ds = pydicom.dcmread(io.BytesIO(b), stop_before_pixels=True)
            st, se, ins = self._id(ds.StudyInstanceUID), self._id(ds.SeriesInstanceUID), self._id(ds.SOPInstanceUID)
            self.instances[ins] = b
            s = self.series.setdefault(se, {"ID": se, "Instances": [], "MainDicomTags": {"Modality": ds.Modality}})
            if ins not in s["Instances"]:
                s["Instances"].append(ins)
            if se not in self.studies.setdefault(st, []):
                self.studies[st].append(se)
            self.changes_log = [c for c in self.changes_log if c["ID"] != st]  # StableStudy fires once quiet
            self.changes_log.append({"Seq": len(self.changes_log) + 1000 + len(self.instances), "ChangeType": "StableStudy", "ID": st})
            return {"ParentStudy": st, "ID": ins}

        def changes(self, since, limit=100):
            new = [c for c in self.changes_log if c["Seq"] > since]
            last = max([c["Seq"] for c in self.changes_log], default=since)
            return {"Changes": new, "Last": max(last, since), "Done": True}

        def study_series(self, sid):
            return [self.series[s] for s in self.studies[sid]]

        def series_instances(self, se):
            return [{"ID": i} for i in self.series[se]["Instances"]]

        def instance_file(self, iid):
            return self.instances[iid]

    fake = FakeOrthanc()
    main.Orthanc = lambda *a, **k: fake  # the lifespan builds the client from this name
    with TestClient(main.app) as c:
        c.fake = fake
        yield c


def token(c, user):
    r = c.post("/api/auth/login", json={"username": user, "password": "pw"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def wait_status(c, h, sid, want, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = c.get(f"/api/studies/{sid}", headers=h).json()
        if st["status"] in want:
            return st
        time.sleep(0.3)
    raise AssertionError(f"study {sid} stuck in {st['status']}: {st.get('error')}")


def test_auth_required(client):
    assert client.get("/api/studies").status_code == 401
    assert client.post("/api/auth/login", json={"username": "dr.a", "password": "nope"}).status_code == 401
    assert client.get("/api/studies", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401


def test_rejects_non_dicom(client):
    h = token(client, "dr.a")
    r = client.post("/api/upload", headers=h, files=[("files", ("x.dcm", b"not a dicom", "application/dicom"))])
    assert r.status_code == 400


def test_xray_flow_classification_gradcam_decision_audit(client):
    h = token(client, "dr.a")
    data = (SAMPLES / "synthetic_cxr_1.dcm").read_bytes()
    r = client.post("/api/upload", headers=h, files=[("files", ("cxr.dcm", data, "application/dicom"))])
    assert r.status_code == 200 and r.json()["accepted"] == 1

    sid = next(s["id"] for s in client.get("/api/studies", headers=h).json())
    st = wait_status(client, h, sid, {"awaiting_review", "failed"})
    assert st["status"] == "awaiting_review", st["error"]
    assert st["has_heatmap"] and st["modality"] == "DX" and st["sex"] == "F"
    assert st["patient_ref"] and "SYN" not in st["patient_ref"]  # pseudonymised
    pred = st["predictions"][0]
    assert pred["task"] == "classification" and 0 <= pred["probability"] <= 1 and len(pred["model_sha256"]) == 64

    img = client.get(f"/api/studies/{sid}/image.png", headers=h)
    hm = client.get(f"/api/studies/{sid}/heatmap.png", headers=h)
    assert img.status_code == hm.status_code == 200 and hm.content[:4] == b"\x89PNG"

    # reject needs a comment; admin cannot decide
    assert client.post(f"/api/predictions/{pred['id']}/decision", headers=h, json={"decision": "reject"}).status_code == 422
    assert client.post(f"/api/predictions/{pred['id']}/decision", headers=token(client, "admin"),
                       json={"decision": "approve"}).status_code == 403
    r = client.post(f"/api/predictions/{pred['id']}/decision", headers=h,
                    json={"decision": "reject", "comment": "opacity is overlying soft tissue"})
    assert r.status_code == 200 and r.json()["latest_decision"]["decision"] == "reject"
    assert client.get(f"/api/studies/{sid}", headers=h).json()["status"] == "reviewed"

    actions = [e["action"] for e in client.get("/api/audit", headers=h).json()]
    for a in ("login", "upload", "inference_completed", "view_study", "decision_reject"):
        assert a in actions
    assert client.get("/api/audit/verify", headers=h).json()["valid"] is True


def test_ct_zip_flow_segmentation(client):
    h = token(client, "dr.a")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f in sorted((SAMPLES / "synthetic_ct").glob("*.dcm")):
            z.write(f, f.name)
    r = client.post("/api/upload", headers=h, files=[("files", ("ct.zip", buf.getvalue(), "application/zip"))])
    assert r.status_code == 200 and r.json()["accepted"] == 40
    sid = next(s["id"] for s in client.get("/api/studies", headers=h).json() if s["modality"] in (None, "CT"))
    st = wait_status(client, h, sid, {"awaiting_review", "failed"}, timeout=300)
    assert st["status"] == "awaiting_review", st["error"]
    assert st["n_slices"] == 40 and st["has_slices"]
    p = st["predictions"][0]
    assert p["task"] == "segmentation" and "volume_ml" in p["details"]
    assert client.get(f"/api/studies/{sid}/slices/0.png", headers=h).status_code == 200
    assert client.get(f"/api/studies/{sid}/slices/0.png?layer=mask", headers=h).status_code in (200, 204)


def test_oauth2_form_token_and_jwt_claims(client):
    import jwt as pyjwt
    r = client.post("/api/auth/token", data={"username": "dr.a", "password": "pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 15 * 60
    claims = pyjwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["typ"] == "access" and claims["role"] == "clinician" and claims["aud"] == "medimg-api"
    assert "password" not in str(claims)
    assert client.get("/api/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()["username"] == "dr.a"


def test_refresh_token_cannot_be_used_as_access_token(client):
    rt = client.post("/api/auth/token", data={"username": "dr.a", "password": "pw"}).json()["refresh_token"]
    assert client.get("/api/me", headers={"Authorization": f"Bearer {rt}"}).status_code == 401


def test_forged_and_expired_tokens_rejected(client):
    import datetime as dt
    import jwt as pyjwt
    now = dt.datetime.now(dt.timezone.utc)
    base = {"sub": "1", "role": "admin", "ver": 0, "typ": "access", "iss": "medimg-capstone", "aud": "medimg-api",
            "iat": now, "jti": "x"}
    forged = pyjwt.encode({**base, "exp": now + dt.timedelta(minutes=5)}, "wrong-secret-wrong-secret-wrong-secret", "HS256")
    expired = pyjwt.encode({**base, "iat": now - dt.timedelta(hours=1), "exp": now - dt.timedelta(minutes=5)},
                           "test-secret-that-is-long-enough-for-hs256", "HS256")
    unsigned = pyjwt.encode({**base, "exp": now + dt.timedelta(minutes=5)}, None, algorithm="none")
    for tok in (forged, expired, unsigned):
        assert client.get("/api/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
    r = client.get("/api/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.json()["detail"] == "token expired" and "invalid_token" in r.headers["www-authenticate"]


def test_refresh_rotation_and_reuse_detection(client):
    t1 = client.post("/api/auth/login", json={"username": "dr.a", "password": "pw"}).json()
    t2 = client.post("/api/auth/refresh", json={"refresh_token": t1["refresh_token"]}).json()
    assert t2["refresh_token"] != t1["refresh_token"]
    assert client.get("/api/me", headers={"Authorization": f"Bearer {t2['access_token']}"}).status_code == 200
    # replaying the old refresh token = theft → whole family revoked, including the new one
    assert client.post("/api/auth/refresh", json={"refresh_token": t1["refresh_token"]}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": t2["refresh_token"]}).status_code == 401


def test_logout_revokes_refresh_token(client):
    t = client.post("/api/auth/login", json={"username": "dr.a", "password": "pw"}).json()
    assert client.post("/api/auth/logout", json={"refresh_token": t["refresh_token"]}).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_admin_user_management_and_deactivation(client):
    admin = token(client, "admin")
    assert client.get("/api/users", headers=token(client, "dr.a")).status_code == 403
    r = client.post("/api/users", headers=admin, json={"username": "Dr.New", "password": "longenough1", "role": "clinician"})
    assert r.status_code == 201 and r.json()["username"] == "dr.new"
    assert client.post("/api/users", headers=admin, json={"username": "x1", "password": "short", "role": "clinician"}).status_code == 422
    t = client.post("/api/auth/login", json={"username": "dr.new", "password": "longenough1"}).json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.get("/api/me", headers=h).status_code == 200
    uid = r.json()["id"]
    assert client.patch(f"/api/users/{uid}", headers=admin, json={"is_active": False}).status_code == 200
    # disabling kills the still-unexpired access token and the refresh token immediately
    assert client.get("/api/me", headers=h).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "dr.new", "password": "longenough1"}).status_code == 401
    me = client.get("/api/me", headers=admin).json()
    assert client.patch(f"/api/users/{me['id']}", headers=admin, json={"is_active": False}).status_code == 400


def test_password_change_signs_out_other_sessions(client):
    t = client.post("/api/auth/login", json={"username": "dr.b", "password": "pw"}).json()
    h = {"Authorization": f"Bearer {t['access_token']}"}
    assert client.post("/api/me/password", headers=h, json={"current_password": "bad", "new_password": "newpass123"}).status_code == 400
    assert client.post("/api/me/password", headers=h, json={"current_password": "pw", "new_password": "newpass123"}).status_code == 204
    assert client.get("/api/me", headers=h).status_code == 401
    assert client.post("/api/auth/login", json={"username": "dr.b", "password": "newpass123"}).status_code == 200


def test_bruteforce_lockout(client):
    for _ in range(3):
        assert client.post("/api/auth/login", json={"username": "dr.b", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "dr.b", "password": "newpass123"})
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_tampering_is_detected(client):
    h = token(client, "dr.a")
    from app.db.db import AuditEvent, SessionLocal
    with SessionLocal() as s:
        ev = s.get(AuditEvent, 2)
        ev.actor = "someone-else"
        s.commit()
    v = client.get("/api/audit/verify", headers=h).json()
    assert v == {"valid": False, "checked": 1, "broken_at_event_id": 2}

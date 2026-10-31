from __future__ import annotations

import io
import logging
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from .services import audit
from .auth.auth import (authenticate, current_user, hash_password, issue_tokens, require_role, revoke_all_for_user,
                   revoke_refresh, rotate_refresh, seed_users, validate_new_password, verify_password)
from .core.config import DISCLAIMER, settings
from .db.db import AuditEvent, Decision, Prediction, SessionLocal, Study, User, init_db
from .services.inference import Registry, artifact_dir
from .services.orthanc import Orthanc
from .workers.worker import Worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.jwt_secret.startswith("dev-only"):
        logging.getLogger("auth").warning("JWT_SECRET is the development default — set it in .env before any real use")
    with SessionLocal() as s:
        if n := seed_users(s):
            logging.getLogger("auth").info("seeded %d user(s) from USERS", n)
    state["registry"] = Registry()
    state["orthanc"] = Orthanc()
    state["worker"] = Worker(state["registry"], state["orthanc"], settings.poll_seconds)
    if settings.enable_worker:
        state["worker"].start()
    yield
    state["worker"].stop()


app = FastAPI(title="AI-Assisted Medical Imaging — decision support (educational)", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


def _openapi():
    """Swagger UI shows a text box (not a file picker) for OpenAPI 3.1 `contentMediaType` arrays.
    Rewrite upload fields to the older `format: binary` form so /docs offers 'Choose file' buttons."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(title=app.title, version="0.1.0", routes=app.routes)
    for comp in schema.get("components", {}).get("schemas", {}).values():
        for prop in comp.get("properties", {}).values():
            items = prop.get("items", {})
            if items.get("contentMediaType") == "application/octet-stream":
                prop["items"] = {"type": "string", "format": "binary"}
    app.openapi_schema = schema
    return schema


app.openapi = _openapi


def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# ---------------------------------------------------------------- schemas
class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str
    role: Literal["clinician", "admin"]
    full_name: str | None = Field(default=None, max_length=128)


class UserUpdateIn(BaseModel):
    role: Literal["clinician", "admin"] | None = None
    is_active: bool | None = None
    full_name: str | None = Field(default=None, max_length=128)
    password: str | None = None


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------- serialisers
def ser_decision(d: Decision) -> dict:
    return {"id": d.id, "reviewer": d.reviewer, "decision": d.decision, "comment": d.comment,
            "created_at": d.created_at.isoformat()}


def ser_prediction(p: Prediction) -> dict:
    return {"id": p.id, "task": p.task, "model_version": p.model_version, "model_sha256": p.model_sha256,
            "label": p.label, "probability": p.probability, "threshold": p.threshold, "positive": p.positive,
            "details": p.details, "inference_ms": p.inference_ms, "is_current": p.is_current,
            "created_at": p.created_at.isoformat(), "decisions": [ser_decision(d) for d in p.decisions],
            "latest_decision": ser_decision(p.decisions[-1]) if p.decisions else None}


def ser_study(s: Study, full: bool = False) -> dict:
    cur = [p for p in s.predictions if p.is_current]
    out = {"id": s.id, "orthanc_id": s.orthanc_id, "patient_ref": s.patient_ref, "sex": s.sex, "age": s.age,
           "modality": s.modality, "description": s.description, "study_date": s.study_date, "status": s.status,
           "error": s.error, "n_slices": s.n_slices, "received_at": s.received_at.isoformat(),
           "ai_summary": ({"label": cur[-1].label, "probability": cur[-1].probability, "positive": cur[-1].positive,
                           "task": cur[-1].task} if cur else None)}
    if full:
        out["predictions"] = [ser_prediction(p) for p in s.predictions]
        d = artifact_dir(s.id)
        out["has_heatmap"] = (d / "heatmap.png").exists()
        out["has_image"] = (d / "image.png").exists()
        out["has_slices"] = (d / "slices").exists()
    return out


# ---------------------------------------------------------------- routes
@app.get("/api/health")
def health():
    try:
        orth = state["orthanc"].system().get("Version")
    except Exception:
        orth = None
    return {"ok": True, "orthanc_version": orth, "models": state["registry"].describe()}


@app.get("/api/info")
def info():
    return {"disclaimer": DISCLAIMER, "models": state["registry"].describe()}


# ---------------------------------------------------------------- auth (OAuth2 password flow + JWT)
def _login(s, username: str, password: str, via: str) -> dict:
    try:
        user = authenticate(s, username, password)
    except HTTPException as e:
        audit.log(s, username.strip().lower()[:64], "login_failed", details={"via": via, "reason": e.detail})
        raise
    audit.log(s, user.username, "login", "user", user.id, {"via": via})
    return issue_tokens(s, user)


@app.post("/api/auth/token", tags=["auth"])
def oauth2_token(form: OAuth2PasswordRequestForm = Depends(), s=Depends(db)):
    """OAuth2 token endpoint (form-encoded `username` + `password`). Used by Swagger's **Authorize** button."""
    return _login(s, form.username, form.password, "oauth2_form")


@app.post("/api/auth/login", tags=["auth"])
def login(body: LoginIn, s=Depends(db)):
    """Same as /api/auth/token but takes JSON — used by the React viewer."""
    return _login(s, body.username, body.password, "json")


@app.post("/api/auth/refresh", tags=["auth"])
def refresh(body: RefreshIn, s=Depends(db)):
    """Exchange a refresh token for a new access + refresh pair. The old refresh token stops working."""
    try:
        user, tokens = rotate_refresh(s, body.refresh_token)
    except HTTPException as e:
        if "reuse" in str(e.detail):
            audit.log(s, "system", "refresh_token_reuse_detected", details={"detail": e.detail})
        raise
    return tokens


@app.post("/api/auth/logout", tags=["auth"], status_code=204)
def logout(body: RefreshIn, s=Depends(db)):
    revoke_refresh(s, body.refresh_token)
    return Response(status_code=204)


@app.get("/api/me", tags=["auth"])
def me(user=Depends(current_user)):
    return user


@app.post("/api/me/password", tags=["auth"], status_code=204)
def change_password(body: PasswordChangeIn, user=Depends(current_user), s=Depends(db)):
    u = s.get(User, user["id"])
    if not verify_password(body.current_password, u.password_hash):
        raise HTTPException(400, "current password is incorrect")
    validate_new_password(body.new_password)
    u.password_hash = hash_password(body.new_password)
    revoke_all_for_user(s, u)  # signs out every other session
    audit.log(s, u.username, "password_changed", "user", u.id)
    return Response(status_code=204)


# ---------------------------------------------------------------- user management (admin)
def ser_user(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None}


@app.get("/api/users", tags=["users"])
def list_users(admin=Depends(require_role("admin")), s=Depends(db)):
    return [ser_user(u) for u in s.scalars(select(User).order_by(User.id))]


@app.post("/api/users", tags=["users"], status_code=201)
def create_user(body: UserCreateIn, admin=Depends(require_role("admin")), s=Depends(db)):
    name = body.username.lower()
    if s.scalar(select(User).where(User.username == name)):
        raise HTTPException(409, "username already exists")
    validate_new_password(body.password)
    u = User(username=name, full_name=body.full_name, role=body.role, password_hash=hash_password(body.password))
    s.add(u)
    s.commit()
    audit.log(s, admin["username"], "user_created", "user", u.id, {"username": name, "role": body.role})
    return ser_user(u)


@app.patch("/api/users/{user_id}", tags=["users"])
def update_user(user_id: int, body: UserUpdateIn, admin=Depends(require_role("admin")), s=Depends(db)):
    u = s.get(User, user_id)
    if not u:
        raise HTTPException(404, "user not found")
    if u.id == admin["id"] and (body.is_active is False or (body.role and body.role != "admin")):
        raise HTTPException(400, "you cannot deactivate or demote yourself")
    changes = body.model_dump(exclude_unset=True, exclude={"password"})
    for k, v in changes.items():
        setattr(u, k, v)
    if body.password is not None:
        validate_new_password(body.password)
        u.password_hash = hash_password(body.password)
        changes["password"] = "reset"
    s.commit()
    if body.password is not None or body.is_active is False:
        revoke_all_for_user(s, u)
    audit.log(s, admin["username"], "user_updated", "user", u.id, changes)
    return ser_user(u)


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...), user=Depends(require_role("clinician", "admin")), s=Depends(db)):
    """Accepts .dcm files and/or .zip archives of DICOM files and forwards them to Orthanc.
    The worker picks the study up from Orthanc's change feed once it is complete."""
    blobs: list[tuple[str, bytes]] = []
    for f in files:
        data = await f.read()
        if f.filename and f.filename.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                blobs += [(n, z.read(n)) for n in z.namelist() if not n.endswith("/")]
        else:
            blobs.append((f.filename or "file", data))
    try:
        state["orthanc"].system()
    except Exception as e:
        raise HTTPException(503, f"Orthanc is not reachable at {settings.orthanc_url} ({type(e).__name__}). "
                                 "Start Orthanc and try again.")
    studies, rejected = set(), []
    for name, b in blobs:
        if len(b) < 132 or b[128:132] != b"DICM":
            rejected.append(name)
            continue
        try:
            studies.add(state["orthanc"].upload(b)["ParentStudy"])
        except Exception as e:
            rejected.append(f"{name}: {e}")
    for sid in studies:
        if not s.scalar(select(Study).where(Study.orthanc_id == sid)):
            s.add(Study(orthanc_id=sid, status="queued"))
    s.commit()
    audit.log(s, user["username"], "upload", "orthanc_study", ",".join(sorted(studies)),
              {"instances": len(blobs) - len(rejected), "rejected": rejected[:20]})
    if not studies:
        raise HTTPException(400, {"message": "no valid DICOM files", "rejected": rejected[:20]})
    return {"studies": sorted(studies), "accepted": len(blobs) - len(rejected), "rejected": rejected}


@app.get("/api/studies")
def list_studies(status: str | None = None, user=Depends(current_user), s=Depends(db)):
    q = select(Study).order_by(Study.received_at.desc())
    if status:
        q = q.where(Study.status == status)
    return [ser_study(x) for x in s.scalars(q)]


def _get_study(s, study_id: int) -> Study:
    st = s.get(Study, study_id)
    if not st:
        raise HTTPException(404, "study not found")
    return st


@app.get("/api/studies/{study_id}")
def get_study(study_id: int, user=Depends(current_user), s=Depends(db)):
    st = _get_study(s, study_id)
    audit.log(s, user["username"], "view_study", "study", st.id)  # access logging for patient data
    return ser_study(st, full=True)


def _png(path: Path):
    if not path.exists():
        raise HTTPException(404, "not available")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, max-age=300"})


@app.get("/api/studies/{study_id}/image.png")
def study_image(study_id: int, user=Depends(current_user)):
    return _png(artifact_dir(study_id) / "image.png")


@app.get("/api/studies/{study_id}/heatmap.png")
def study_heatmap(study_id: int, user=Depends(current_user)):
    return _png(artifact_dir(study_id) / "heatmap.png")


@app.get("/api/studies/{study_id}/slices/{k}.png")
def study_slice(study_id: int, k: int, layer: Literal["image", "mask"] = "image", user=Depends(current_user)):
    p = artifact_dir(study_id) / ("slices" if layer == "image" else "mask") / f"{k:04d}.png"
    if layer == "mask" and not p.exists():
        return Response(status_code=204)  # no mask on this slice
    return _png(p)


@app.post("/api/predictions/{pred_id}/decision")
def decide(pred_id: int, body: DecisionIn, user=Depends(require_role("clinician")), s=Depends(db)):
    p = s.get(Prediction, pred_id)
    if not p:
        raise HTTPException(404, "prediction not found")
    if not p.is_current:
        raise HTTPException(409, "prediction superseded by a newer model run")
    if body.decision == "reject" and not (body.comment or "").strip():
        raise HTTPException(422, "a comment is required when rejecting an AI result")
    d = Decision(reviewer=user["username"], decision=body.decision, comment=body.comment)
    p.decisions.append(d)
    s.flush()
    st = p.study
    if all(q.decisions for q in st.predictions if q.is_current):
        st.status = "reviewed"
    s.commit()
    audit.log(s, user["username"], f"decision_{body.decision}", "prediction", p.id,
              {"study_id": st.id, "decision_id": d.id, "model_version": p.model_version, "ai_label": p.label,
               "ai_probability": p.probability, "comment": body.comment,
               "changed_previous": len(p.decisions) > 1})
    return ser_prediction(p)


@app.post("/api/studies/{study_id}/reprocess")
def reprocess(study_id: int, user=Depends(require_role("admin")), s=Depends(db)):
    st = _get_study(s, study_id)
    st.status = "queued"
    s.commit()
    state["worker"].enqueue(st.orthanc_id, user["username"])
    audit.log(s, user["username"], "reprocess_requested", "study", st.id)
    return {"queued": True}


@app.post("/api/admin/reload-models")
def reload_models(user=Depends(require_role("admin")), s=Depends(db)):
    state["registry"].reload()
    audit.log(s, user["username"], "models_reloaded", details={"models": state["registry"].describe()})
    return state["registry"].describe()


@app.get("/api/audit")
def audit_log(limit: int = 200, entity_type: str | None = None, entity_id: str | None = None,
              user=Depends(current_user), s=Depends(db)):
    q = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(min(limit, 1000))
    if entity_type:
        q = q.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditEvent.entity_id == entity_id)
    return [{"id": e.id, "ts": e.ts.isoformat(), "actor": e.actor, "action": e.action, "entity_type": e.entity_type,
             "entity_id": e.entity_id, "details": e.details, "hash": e.hash[:12]} for e in s.scalars(q)]


@app.get("/api/audit/verify")
def audit_verify(user=Depends(current_user), s=Depends(db)):
    return audit.verify(s)


@app.get("/api/stats")
def stats(user=Depends(current_user), s=Depends(db)):
    by_status = dict(s.execute(select(Study.status, func.count()).group_by(Study.status)).all())
    by_dec = dict(s.execute(select(Decision.decision, func.count()).group_by(Decision.decision)).all())
    return {"studies_by_status": by_status, "decisions": by_dec}

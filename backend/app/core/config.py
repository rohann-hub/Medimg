from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _users(raw: str) -> dict[str, dict]:
    """USERS="dr.rao:changeme:clinician,admin:changeme:admin" → {username: {password, role}}."""
    out = {}
    for item in filter(None, (s.strip() for s in raw.split(","))):
        name, pw, role = item.split(":")
        out[name] = {"password": pw, "role": role}
    return out


@dataclass
class Settings:
    orthanc_url: str = os.getenv("ORTHANC_URL", "http://localhost:8042")
    orthanc_user: str = os.getenv("ORTHANC_USER", "orthanc")
    orthanc_password: str = os.getenv("ORTHANC_PASSWORD", "orthanc")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./var/app.db")
    artifact_dir: Path = Path(os.getenv("ARTIFACT_DIR", "./var/artifacts"))
    cls_model_path: Path = Path(os.getenv("CLS_MODEL_PATH", "../models/classifier.pt"))
    seg_model_path: Path = Path(os.getenv("SEG_MODEL_PATH", "../models/segmentation.pt"))
    poll_seconds: float = float(os.getenv("POLL_SECONDS", "3"))
    enable_worker: bool = os.getenv("ENABLE_WORKER", "1") == "1"
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-change-me")
    token_ttl_hours: int = int(os.getenv("TOKEN_TTL_HOURS", "12"))
    patient_salt: str = os.getenv("PATIENT_ID_SALT", "dev-salt-change-me")
    users: dict = field(default_factory=lambda: _users(os.getenv("USERS", "dr.demo:demo123:clinician,admin:admin123:admin")))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))


settings = Settings()
settings.artifact_dir.mkdir(parents=True, exist_ok=True)

DISCLAIMER = (
    "EDUCATIONAL / RESEARCH USE ONLY. Not a medical device. AI outputs are decision-support "
    "suggestions that must be reviewed by a qualified clinician and must not be used as a diagnosis."
)

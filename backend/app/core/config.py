from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Load the project-root .env when running without Docker (uvicorn from backend/).
# Real environment variables (e.g. from docker-compose) always win over the file.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)  # core -> app -> backend -> project root
except ImportError:  # python-dotenv not installed → rely on real env vars only
    pass


def _users(raw: str) -> dict[str, dict]:
    """USERS="dr.rao:changeme:clinician,admin:changeme:admin" → {username: {password, role}}.
    Used ONLY to seed the users table on first start (empty table). After that, manage users via /api/users."""
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
    # --- JWT / OAuth2 ---
    jwt_secret: str = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "dev-only-change-me-to-32+-random-bytes"))
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "medimg-capstone")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "medimg-api")
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
    refresh_token_days: int = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
    login_max_failures: int = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
    login_lockout_minutes: int = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
    patient_salt: str = os.getenv("PATIENT_ID_SALT", "dev-salt-change-me")
    users: dict = field(default_factory=lambda: _users(os.getenv("USERS", "dr.demo:demo123:clinician,admin:admin123:admin")))
    cors_origins: list[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","))


settings = Settings()
settings.artifact_dir.mkdir(parents=True, exist_ok=True)

DISCLAIMER = (
    "EDUCATIONAL / RESEARCH USE ONLY. Not a medical device. AI outputs are decision-support "
    "suggestions that must be reviewed by a qualified clinician and must not be used as a diagnosis."
)

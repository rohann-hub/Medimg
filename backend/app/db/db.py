from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from ..core.config import settings

if settings.database_url.startswith("sqlite:///./"):
    from pathlib import Path
    Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Study(Base):
    __tablename__ = "studies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    orthanc_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    study_uid: Mapped[str | None] = mapped_column(String(128))
    patient_ref: Mapped[str | None] = mapped_column(String(32))  # salted hash — never the raw PatientID
    sex: Mapped[str | None] = mapped_column(String(4))
    age: Mapped[float | None] = mapped_column(Float)
    modality: Mapped[str | None] = mapped_column(String(16))
    description: Mapped[str | None] = mapped_column(String(256))
    study_date: Mapped[str | None] = mapped_column(String(16))
    # queued → processing → awaiting_review → reviewed   |  failed  |  no_model
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    n_slices: Mapped[int] = mapped_column(Integer, default=1)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="study", order_by="Prediction.id",
                                                           cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), index=True)
    task: Mapped[str] = mapped_column(String(32))  # classification | segmentation
    model_version: Mapped[str] = mapped_column(String(128))
    model_sha256: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(64))
    probability: Mapped[float] = mapped_column(Float)  # top-class probability / mean mask confidence
    threshold: Mapped[float | None] = mapped_column(Float)
    positive: Mapped[bool] = mapped_column(Boolean)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    inference_ms: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)  # False after a re-run supersedes it
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    study: Mapped[Study] = relationship(back_populates="predictions")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="prediction", order_by="Decision.id",
                                                       cascade="all, delete-orphan")


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16))  # approve | reject
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    prediction: Mapped[Prediction] = relationship(back_populates="decisions")


class AuditEvent(Base):
    """Append-only. Each row stores the hash of the previous row, so any edit or deletion
    breaks the chain and is detected by /api/audit/verify (tamper-evidence, not tamper-proofing)."""

    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(128))
    password_hash: Mapped[str] = mapped_column(String(128))  # bcrypt — the password itself is never stored
    role: Mapped[str] = mapped_column(String(16))  # clinician | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)  # bump → every issued access token dies
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    """One row per issued refresh token. Rotation: each use revokes the row and issues a new one in the same
    family. Presenting an already-revoked token = theft signal → the whole family is revoked."""

    __tablename__ = "refresh_tokens"
    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    family: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KV(Base):
    __tablename__ = "kv"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256))


def init_db() -> None:
    Base.metadata.create_all(engine)

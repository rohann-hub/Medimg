from __future__ import annotations

import hashlib
import json
import threading
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.db import AuditEvent, now

GENESIS = "0" * 64
_lock = threading.Lock()  # serialise writers so two events never share a prev_hash


def _digest(prev_hash: str, ts: str, actor: str, action: str, entity_type, entity_id, details: dict) -> str:
    payload = json.dumps([prev_hash, ts, actor, action, entity_type, entity_id, details], sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def log(db: Session, actor: str, action: str, entity_type: str | None = None, entity_id=None,
        details: dict | None = None) -> AuditEvent:
    details = details or {}
    entity_id = None if entity_id is None else str(entity_id)
    with _lock:
        last = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1)).first()
        prev = last.hash if last else GENESIS
        ts = now()
        ev = AuditEvent(ts=ts, actor=actor, action=action, entity_type=entity_type, entity_id=entity_id,
                        details=details, prev_hash=prev,
                        hash=_digest(prev, ts.isoformat(), actor, action, entity_type, entity_id, details))
        db.add(ev)
        db.commit()
    return ev


def verify(db: Session) -> dict:
    prev, n = GENESIS, 0
    for ev in db.scalars(select(AuditEvent).order_by(AuditEvent.id)):
        ts = ev.ts if ev.ts.tzinfo else ev.ts.replace(tzinfo=timezone.utc)  # SQLite drops tzinfo
        expect = _digest(prev, ts.isoformat(), ev.actor, ev.action, ev.entity_type, ev.entity_id, ev.details)
        if ev.prev_hash != prev or ev.hash != expect:
            return {"valid": False, "checked": n, "broken_at_event_id": ev.id}
        prev, n = ev.hash, n + 1
    return {"valid": True, "checked": n}

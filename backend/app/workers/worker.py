"""Background service: watch Orthanc's change feed and run AI on every newly *completed* study.

This is the 'retrieve newly uploaded studies + run inference automatically' part of the brief.
It works for studies arriving from ANY source — our upload endpoint, Orthanc Explorer's
upload page, or a real modality/PACS sending via DICOM C-STORE to port 4242.
"""
from __future__ import annotations

import logging
import queue
import threading

from ..db.db import KV, SessionLocal
from ..services.inference import Registry, process_study
from ..services.orthanc import Orthanc

log = logging.getLogger("worker")


class Worker:
    def __init__(self, registry: Registry, orthanc: Orthanc, poll_seconds: float):
        self.reg, self.orthanc, self.poll = registry, orthanc, poll_seconds
        self.jobs: queue.Queue[tuple[str, str]] = queue.Queue()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # --- change-feed cursor persisted in the DB so restarts don't re-process or skip studies ---
    def _get_seq(self, db) -> int | None:
        row = db.get(KV, "orthanc_change_seq")
        return int(row.value) if row else None

    def _set_seq(self, db, seq: int) -> None:
        row = db.get(KV, "orthanc_change_seq") or KV(key="orthanc_change_seq", value="0")
        row.value = str(seq)
        db.merge(row)
        db.commit()

    def enqueue(self, orthanc_study_id: str, actor: str = "system") -> None:
        self.jobs.put((orthanc_study_id, actor))

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    seq = self._get_seq(db)
                    if seq is None:  # first boot: process everything already stored in Orthanc
                        seq = 0
                    while True:
                        ch = self.orthanc.changes(seq)
                        for c in ch.get("Changes", []):
                            if c["ChangeType"] == "StableStudy":
                                log.info("new stable study %s", c["ID"])
                                self.enqueue(c["ID"])
                        seq = int(ch.get("Last", seq))
                        self._set_seq(db, seq)
                        if ch.get("Done", True):
                            break
            except Exception as e:  # Orthanc not up yet, network blip …
                log.warning("poll failed: %s", e)
            self._stop.wait(self.poll)

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                sid, actor = self.jobs.get(timeout=1)
            except queue.Empty:
                continue
            with SessionLocal() as db:
                process_study(db, self.reg, self.orthanc, sid, actor)

    def start(self) -> None:
        for fn in (self._poll_loop, self._run_loop):
            t = threading.Thread(target=fn, daemon=True, name=fn.__name__)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()

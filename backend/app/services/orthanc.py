"""Thin client for the Orthanc REST API (https://orthanc.uclouvain.be/book/users/rest.html)."""
from __future__ import annotations

import httpx

from ..core.config import settings


class Orthanc:
    def __init__(self, url: str | None = None, user: str | None = None, password: str | None = None):
        self.c = httpx.Client(base_url=url or settings.orthanc_url,
                              auth=(user or settings.orthanc_user, password or settings.orthanc_password),
                              timeout=60)

    def system(self) -> dict:
        return self.c.get("/system").raise_for_status().json()

    def upload(self, dicom_bytes: bytes) -> dict:
        """POST /instances — Orthanc parses the file and files it under patient/study/series."""
        return self.c.post("/instances", content=dicom_bytes,
                           headers={"Content-Type": "application/dicom"}).raise_for_status().json()

    def changes(self, since: int, limit: int = 100) -> dict:
        """The change feed. 'StableStudy' fires once no new instance has arrived for StableAge seconds,
        i.e. the whole study has been received — that is when we run inference."""
        return self.c.get("/changes", params={"since": since, "limit": limit}).raise_for_status().json()

    def last_change_seq(self) -> int:
        return int(self.c.get("/changes", params={"last": ""}).raise_for_status().json().get("Last", 0))

    def study(self, sid: str) -> dict:
        return self.c.get(f"/studies/{sid}").raise_for_status().json()

    def study_series(self, sid: str) -> list[dict]:
        return self.c.get(f"/studies/{sid}/series").raise_for_status().json()

    def series_instances(self, series_id: str) -> list[dict]:
        return self.c.get(f"/series/{series_id}/instances").raise_for_status().json()

    def instance_file(self, iid: str) -> bytes:
        return self.c.get(f"/instances/{iid}/file").raise_for_status().content

    def delete_study(self, sid: str) -> None:
        self.c.delete(f"/studies/{sid}").raise_for_status()

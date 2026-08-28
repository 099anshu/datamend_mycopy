"""
Audit logging for dataset changes (Objective #8: "Ensure privacy, security
and auditability across the complete workflow").

Every time a user or the ML pipeline changes a dataset - ingesting it from
a live API, running corruption injection, handling missing values, applying
a repair, or running rule-based validation - an AuditEvent is appended here.

This is a lightweight, file-backed JSONL store so it works standalone with
no new infra. It mirrors the on-disk pattern already used by
`datasets/upload_store.py` (`DATAMEND_UPLOAD_DIR`), and is intentionally
easy to swap for a Postgres-backed table in the Spring Boot backend later:
each AuditEvent maps 1:1 to a future `audit_log` row (dataset_id, actor,
action, details, created_at).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Actor = Literal["user", "model", "system"]


class AuditEvent(BaseModel):
    eventId: str = Field(default_factory=lambda: uuid.uuid4().hex)
    datasetId: str
    actor: Actor
    action: str
    details: Dict[str, Any] = {}
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _log_path() -> Path:
    path = Path(os.environ.get("DATAMEND_AUDIT_DIR", "data/audit")) / "audit_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_event(
    dataset_id: str,
    actor: Actor,
    action: str,
    details: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """Append one audit event and return it."""
    event = AuditEvent(datasetId=dataset_id, actor=actor, action=action, details=details or {})
    with _log_path().open("a", encoding="utf-8") as f:
        f.write(event.model_dump_json() + "\n")
    return event


def get_audit_trail(dataset_id: Optional[str] = None) -> List[AuditEvent]:
    """Return all recorded events, optionally filtered to one dataset."""
    path = _log_path()
    if not path.exists():
        return []
    events: List[AuditEvent] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = AuditEvent.model_validate_json(line)
            if dataset_id is None or event.datasetId == dataset_id:
                events.append(event)
    return events

"""JSON-lines lead log. Good enough for MVP; swap for Postgres later.

Without a mounted disk the file is ephemeral — every accepted lead is also
emitted as structured JSON on stdout (phone masked) so nothing is silently lost.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from threading import Lock

from . import config
from .models import LeadRecord

_LOCK = Lock()
_log = logging.getLogger("zaptu.storage")


def _path() -> Path:
    return config.settings.data_dir / "leads.jsonl"


def mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return f"+{'*' * (len(digits) - 4)}{digits[-4:]}"


def _stdout_lead_event(record: LeadRecord) -> None:
    event = {
        "event": "lead_accepted",
        "lead_id": record.id,
        "status": record.status.value,
        "service_type": record.request.service_type,
        "zip_code": record.request.zip_code,
        "phone_masked": mask_phone(record.request.customer_phone),
        "source_agent": record.request.source_agent,
        "created_at": record.created_at.isoformat(),
    }
    sys.stdout.write(json.dumps(event, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def append_lead(record: LeadRecord) -> None:
    _stdout_lead_event(record)
    line = record.model_dump_json() + "\n"
    with _LOCK:
        try:
            config.settings.data_dir.mkdir(parents=True, exist_ok=True)
            with _path().open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError as exc:
            _log.error("failed to persist lead %s to disk: %s", record.id, exc)


def get_lead(lead_id: str) -> LeadRecord | None:
    path = _path()
    try:
        if not path.exists():
            return None
    except OSError:
        return None
    with _LOCK:
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("id") == lead_id:
                        return LeadRecord.model_validate(data)
        except OSError as exc:
            _log.error("failed to read lead log: %s", exc)
            return None
    return None


def list_leads(limit: int = 50) -> list[LeadRecord]:
    path = _path()
    try:
        if not path.exists():
            return []
    except OSError:
        return []
    rows: list[LeadRecord] = []
    with _LOCK:
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    rows.append(LeadRecord.model_validate_json(line))
        except OSError as exc:
            _log.error("failed to list leads: %s", exc)
            return []
    return rows[-limit:]

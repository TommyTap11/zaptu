"""JSON-lines lead log. Good enough for MVP; swap for Postgres later."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .config import settings
from .models import LeadRecord

_LOCK = Lock()


def _path() -> Path:
    return settings.data_dir / "leads.jsonl"


def append_lead(record: LeadRecord) -> None:
    line = record.model_dump_json() + "\n"
    with _LOCK:
        with _path().open("a", encoding="utf-8") as handle:
            handle.write(line)


def get_lead(lead_id: str) -> LeadRecord | None:
    path = _path()
    if not path.exists():
        return None
    with _LOCK:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("id") == lead_id:
                    return LeadRecord.model_validate(data)
    return None


def list_leads(limit: int = 50) -> list[LeadRecord]:
    path = _path()
    if not path.exists():
        return []
    rows: list[LeadRecord] = []
    with _LOCK:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rows.append(LeadRecord.model_validate_json(line))
    return rows[-limit:]

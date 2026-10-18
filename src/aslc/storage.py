"""Lead storage.

If DATABASE_URL is set, leads are stored in Postgres (Supabase-compatible,
table ``leads``, full record kept as JSON text in ``payload``) so they
survive Render restarts/redeploys. Otherwise a JSON-lines log at
<data_dir>/leads.jsonl is used (local/tests).

Without a mounted disk the JSONL file is ephemeral — every accepted lead is
also emitted as structured JSON on stdout (phone masked) either way, so
nothing is silently lost.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from threading import Lock

from . import config, db
from .models import LeadRecord

_LOCK = Lock()
_log = logging.getLogger("zaptu.storage")


# --- Postgres backend (DATABASE_URL set) ---
# Seam for tests: monkeypatch storage._pg_connect with a fake factory.

def _pg_connect():
    return db.connect_postgres()


_PG_DDL = (
    "CREATE TABLE IF NOT EXISTS leads ("
    "seq BIGSERIAL, id TEXT PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL, payload TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS leads_created_at ON leads(created_at)",
)


def _pg_ensure(con) -> None:
    cur = con.cursor()
    for stmt in _PG_DDL:
        cur.execute(stmt)
    con.commit()


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
    line = record.model_dump_json()
    if db.use_postgres():
        with _LOCK:
            try:
                con = _pg_connect()
                try:
                    _pg_ensure(con)
                    cur = con.cursor()
                    cur.execute(
                        "INSERT INTO leads (id, created_at, payload) VALUES (%s,%s,%s)",
                        (record.id, record.created_at, line),
                    )
                    con.commit()
                finally:
                    con.close()
            except Exception as exc:
                _log.error("failed to persist lead %s to Postgres: %s", record.id, exc)
        return
    line = line + "\n"
    with _LOCK:
        try:
            config.settings.data_dir.mkdir(parents=True, exist_ok=True)
            with _path().open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError as exc:
            _log.error("failed to persist lead %s to disk: %s", record.id, exc)


def get_lead(lead_id: str) -> LeadRecord | None:
    if db.use_postgres():
        with _LOCK:
            try:
                con = _pg_connect()
                try:
                    _pg_ensure(con)
                    cur = con.cursor()
                    cur.execute("SELECT payload FROM leads WHERE id=%s", (lead_id,))
                    row = cur.fetchone()
                finally:
                    con.close()
            except Exception as exc:
                _log.error("failed to read lead %s from Postgres: %s", lead_id, exc)
                return None
        return LeadRecord.model_validate_json(row[0]) if row else None
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
    if db.use_postgres():
        with _LOCK:
            try:
                con = _pg_connect()
                try:
                    _pg_ensure(con)
                    cur = con.cursor()
                    cur.execute("SELECT payload FROM leads ORDER BY seq DESC LIMIT %s", (max(0, int(limit)),))
                    payloads = [r[0] for r in cur.fetchall()]
                finally:
                    con.close()
            except Exception as exc:
                _log.error("failed to list leads from Postgres: %s", exc)
                return []
        return [LeadRecord.model_validate_json(p) for p in reversed(payloads)]
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

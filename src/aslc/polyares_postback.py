"""Polyares conversion postback (Path B).

GET or POST https://api.zaptu.ai/v1/polyares-postback

Accepts a query-string postback or a JSON body (form-urlencoded POST is
treated like a query string). This only records the conversion. It does not
submit a lead and does not call buyer forwarding.

Fields: clickid, event, lead_id, payout, category, sub1, sub2, sub3,
timestamp, delivery_id. event is lead, call, or return.

Idempotency key is delivery_id when present, otherwise lead_id. A repeat
with the same key updates that row (payout, event, category, and the rest).
A different delivery_id is a new row even when lead_id matches, so a later
call or return is not collapsed into the lead. Send a unique delivery_id
per event. Omitting delivery_id means every event for that lead_id shares
one row.

HMAC: set POLYARE_POSTBACK_SECRET in the environment (never in the repo).
When it is unset, the postback is accepted and a warning is logged. When it
is set, the request must carry a lowercase hex HMAC-SHA256 (optional
``sha256=`` prefix) in the X-Polyares-Signature or X-Signature header, or in
a signature / sig / hash field. The signed message may be any of:

- the canonical field string: present fields, sorted by name, ``key=value``
  joined with ``&`` (empty fields omitted; signature fields omitted)
- the raw POST body
- the query string with signature fields removed (original or sorted order)

Compare with hmac.compare_digest. POLYARE_POSTBACK_SECRET is also accepted
as an alias so a correctly spelled env var still verifies.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock
from urllib.parse import parse_qs, parse_qsl

from starlette.requests import Request
from starlette.responses import JSONResponse

from . import config, db

_log = logging.getLogger("zaptu.polyares")
_LOCK = Lock()

EVENTS = frozenset({"lead", "call", "return"})
FIELDS = (
    "clickid",
    "event",
    "lead_id",
    "payout",
    "category",
    "sub1",
    "sub2",
    "sub3",
    "timestamp",
    "delivery_id",
)
_SIGNATURE_KEYS = frozenset({"signature", "sig", "hash"})
_SECRET_ENVS = ("POLYARE_POSTBACK_SECRET", "POLYARES_POSTBACK_SECRET")
_LIMITS = {
    "clickid": 200,
    "event": 32,
    "lead_id": 200,
    "payout": 32,
    "category": 64,
    "sub1": 200,
    "sub2": 200,
    "sub3": 200,
    "timestamp": 64,
    "delivery_id": 200,
}

_PG_DDL = (
    "CREATE TABLE IF NOT EXISTS polyares_conversions ("
    "idem_key TEXT PRIMARY KEY, "
    "delivery_id TEXT, "
    "lead_id TEXT, "
    "clickid TEXT, "
    "event TEXT NOT NULL, "
    "payout NUMERIC, "
    "category TEXT, "
    "sub1 TEXT, "
    "sub2 TEXT, "
    "sub3 TEXT, "
    "event_timestamp TEXT, "
    "payload TEXT NOT NULL, "
    "received_at TIMESTAMPTZ NOT NULL, "
    "updated_at TIMESTAMPTZ NOT NULL)",
    "CREATE INDEX IF NOT EXISTS polyares_conversions_lead_id ON polyares_conversions (lead_id)",
    "CREATE INDEX IF NOT EXISTS polyares_conversions_received_at ON polyares_conversions (received_at)",
)

_UPSERT_SQL = (
    "INSERT INTO polyares_conversions ("
    "idem_key, delivery_id, lead_id, clickid, event, payout, category, "
    "sub1, sub2, sub3, event_timestamp, payload, received_at, updated_at"
    ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
    "ON CONFLICT (idem_key) DO UPDATE SET "
    "delivery_id=EXCLUDED.delivery_id, "
    "lead_id=EXCLUDED.lead_id, "
    "clickid=EXCLUDED.clickid, "
    "event=EXCLUDED.event, "
    "payout=EXCLUDED.payout, "
    "category=EXCLUDED.category, "
    "sub1=EXCLUDED.sub1, "
    "sub2=EXCLUDED.sub2, "
    "sub3=EXCLUDED.sub3, "
    "event_timestamp=EXCLUDED.event_timestamp, "
    "payload=EXCLUDED.payload, "
    "updated_at=EXCLUDED.updated_at"
)


class PostbackError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def postback_secret() -> str | None:
    """Return the HMAC secret, or None when verification is not configured."""
    for name in _SECRET_ENVS:
        raw = (os.getenv(name) or "").strip()
        if raw:
            return raw
    return None


def canonical_message(fields: dict[str, str]) -> str:
    """Sorted ``key=value`` string of the present postback fields."""
    parts: list[str] = []
    for key in sorted(FIELDS):
        val = fields.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if not text:
            continue
        parts.append(f"{key}={text}")
    return "&".join(parts)


def _pg_connect():
    return db.connect_postgres()


def _jsonl_path():
    return config.settings.data_dir / "polyares_conversions.jsonl"


def _as_text(value: object) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        try:
            return format(Decimal(str(value)), "f")
        except InvalidOperation:
            return ""
    return str(value).strip()


def _known_fields(data: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, value in data.items():
        name = str(key)
        if name not in FIELDS:
            continue
        text = _as_text(value)
        if text:
            found[name] = text
    return found


def _signatures(data: dict, headers) -> list[str]:
    sigs: list[str] = []
    if headers is not None:
        for name in ("x-polyares-signature", "x-signature"):
            val = headers.get(name)
            if val and str(val).strip():
                sigs.append(str(val).strip())
    for key in list(data.keys()):
        if str(key).lower() in _SIGNATURE_KEYS:
            val = data.get(key)
            if val is not None and str(val).strip():
                sigs.append(str(val).strip())
    return sigs


def _query_messages(query_string: bytes) -> list[bytes]:
    if not query_string:
        return []
    pairs = parse_qsl(query_string.decode("utf-8", "replace"), keep_blank_values=True)
    kept = [(k, v) for k, v in pairs if k.lower() not in _SIGNATURE_KEYS]
    if not kept:
        return []

    def _join(items: list[tuple[str, str]]) -> bytes:
        return "&".join(f"{k}={v}" for k, v in items).encode("utf-8")

    ordered = _join(kept)
    ranked = _join(sorted(kept))
    if ranked == ordered:
        return [ordered]
    return [ordered, ranked]


def _digest_ok(secret: str, message: bytes, provided: str) -> bool:
    token = provided.strip()
    if token.lower().startswith("sha256="):
        token = token[7:].strip()
    token = token.lower()
    if len(token) != 64 or any(ch not in "0123456789abcdef" for ch in token):
        return False
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)


def _verify(secret: str, fields: dict[str, str], raw_body: bytes, query_string: bytes, signatures: list[str]) -> None:
    if not signatures:
        raise PostbackError(401, "invalid_signature", "Missing signature.")
    messages = [canonical_message(fields).encode("utf-8")]
    if raw_body:
        messages.append(raw_body)
    messages.extend(_query_messages(query_string))
    for sig in signatures:
        for message in messages:
            if _digest_ok(secret, message, sig):
                return
    raise PostbackError(401, "invalid_signature", "Invalid signature.")


def _bounded(fields: dict[str, str], name: str) -> str | None:
    text = fields.get(name)
    if not text:
        return None
    if len(text) > _LIMITS[name]:
        raise PostbackError(422, "invalid_request", f"{name} is too long.")
    return text


def _payout(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        raise PostbackError(422, "invalid_request", "payout must be a number.") from None
    if not amount.is_finite() or amount < 0 or amount > Decimal("1000000"):
        raise PostbackError(422, "invalid_request", "payout must be a number from 0 to 1000000.")
    return format(amount, "f")


def _validate(fields: dict[str, str]) -> dict[str, str | None]:
    event = (_bounded(fields, "event") or "").lower()
    if event not in EVENTS:
        raise PostbackError(422, "invalid_request", "event must be lead, call, or return.")
    delivery_id = _bounded(fields, "delivery_id")
    lead_id = _bounded(fields, "lead_id")
    if not delivery_id and not lead_id:
        raise PostbackError(422, "invalid_request", "delivery_id or lead_id is required.")
    return {
        "clickid": _bounded(fields, "clickid"),
        "event": event,
        "lead_id": lead_id,
        "payout": _payout(_bounded(fields, "payout")),
        "category": _bounded(fields, "category"),
        "sub1": _bounded(fields, "sub1"),
        "sub2": _bounded(fields, "sub2"),
        "sub3": _bounded(fields, "sub3"),
        "timestamp": _bounded(fields, "timestamp"),
        "delivery_id": delivery_id,
        "idem_key": f"d:{delivery_id}" if delivery_id else f"l:{lead_id}",
    }


def _pg_ensure(con) -> None:
    cur = con.cursor()
    for stmt in _PG_DDL:
        cur.execute(stmt)
    con.commit()


def _load_jsonl() -> dict[str, dict]:
    path = _jsonl_path()
    rows: dict[str, dict] = {}
    try:
        if not path.exists():
            return rows
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error("failed to read polyares conversions: %s", exc)
        raise PostbackError(503, "storage_unavailable", "Could not store conversion. Retry.") from exc
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            _log.error("polyares conversions log is unreadable: %s", exc)
            raise PostbackError(503, "storage_unavailable", "Could not store conversion. Retry.") from exc
        key = row.get("idem_key")
        if key:
            rows[str(key)] = row
    return rows


def _save_jsonl(rows: dict[str, dict]) -> None:
    path = _jsonl_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(json.dumps(rows[key], separators=(",", ":")) + "\n" for key in rows)
        tmp = path.with_suffix(".jsonl.tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        _log.error("failed to write polyares conversions: %s", exc)
        raise PostbackError(503, "storage_unavailable", "Could not store conversion. Retry.") from exc


def _pg_get(con, idem_key: str) -> dict | None:
    cur = con.cursor()
    cur.execute("SELECT payload FROM polyares_conversions WHERE idem_key=%s", (idem_key,))
    row = cur.fetchone()
    if not row:
        return None
    return json.loads(row[0])


def _pg_upsert(con, record: dict, received_at: datetime, updated_at: datetime) -> None:
    payout = Decimal(record["payout"]) if record.get("payout") else None
    params = (
        record["idem_key"],
        record.get("delivery_id"),
        record.get("lead_id"),
        record.get("clickid"),
        record["event"],
        payout,
        record.get("category"),
        record.get("sub1"),
        record.get("sub2"),
        record.get("sub3"),
        record.get("timestamp"),
        json.dumps(record, separators=(",", ":")),
        received_at,
        updated_at,
    )
    cur = con.cursor()
    cur.execute(_UPSERT_SQL, params)
    con.commit()


def upsert_conversion(record: dict) -> bool:
    """Insert or update by idem_key. Returns True when the key already existed."""
    now = datetime.now(timezone.utc)
    key = record["idem_key"]
    with _LOCK:
        if db.use_postgres():
            try:
                con = _pg_connect()
                try:
                    _pg_ensure(con)
                    existing = _pg_get(con, key)
                    if existing and existing.get("received_at"):
                        received_at = datetime.fromisoformat(existing["received_at"])
                        duplicate = True
                    else:
                        received_at = now
                        duplicate = False
                    stored = dict(record)
                    stored["received_at"] = received_at.isoformat()
                    stored["updated_at"] = now.isoformat()
                    _pg_upsert(con, stored, received_at, now)
                finally:
                    con.close()
            except PostbackError:
                raise
            except Exception as exc:
                _log.error("failed to persist polyares conversion %s: %s", key, exc)
                raise PostbackError(503, "storage_unavailable", "Could not store conversion. Retry.") from exc
            record.clear()
            record.update(stored)
            return duplicate

        rows = _load_jsonl()
        existing = rows.get(key)
        duplicate = existing is not None
        stored = dict(record)
        stored["received_at"] = existing["received_at"] if existing else now.isoformat()
        stored["updated_at"] = now.isoformat()
        rows[key] = stored
        _save_jsonl(rows)
        record.clear()
        record.update(stored)
        return duplicate


def list_conversions() -> list[dict]:
    """Stored conversions, oldest first. Used by tests and local inspection."""
    if db.use_postgres():
        with _LOCK:
            try:
                con = _pg_connect()
                try:
                    _pg_ensure(con)
                    cur = con.cursor()
                    cur.execute(
                        "SELECT payload FROM polyares_conversions ORDER BY received_at, idem_key"
                    )
                    payloads = [row[0] for row in cur.fetchall()]
                finally:
                    con.close()
            except Exception as exc:
                _log.error("failed to list polyares conversions: %s", exc)
                return []
        return [json.loads(payload) for payload in payloads]
    try:
        rows = _load_jsonl()
    except PostbackError:
        return []
    return list(rows.values())


def record_postback(data: dict, *, raw_body: bytes, query_string: bytes, headers) -> dict:
    """Validate, verify, and store one postback. Returns event and duplicate flag."""
    incoming = dict(data)
    signatures = _signatures(incoming, headers)
    fields = _known_fields(incoming)
    secret = postback_secret()
    if secret:
        _verify(secret, fields, raw_body, query_string, signatures)
    record = _validate(fields)
    duplicate = upsert_conversion(record)
    if not secret:
        _log.warning(
            "POLYARE_POSTBACK_SECRET is unset; accepting Polyares postback without HMAC verification"
        )
    _log.info(
        "polyares_postback event=%s category=%s payout=%s duplicate=%s",
        record.get("event") or "",
        record.get("category") or "",
        record.get("payout") or "",
        duplicate,
    )
    return {"event": record["event"], "duplicate": duplicate}


def _parse_body(content_type: str, raw: bytes) -> dict:
    if not raw:
        return {}
    ctype = (content_type or "").lower()
    stripped = raw.lstrip()
    if "application/json" in ctype or stripped.startswith(b"{") or stripped.startswith(b"["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise PostbackError(422, "invalid_request", "JSON body must be an object.") from None
        if not isinstance(parsed, dict):
            raise PostbackError(422, "invalid_request", "JSON body must be an object.")
        return parsed
    form = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in form.items()}


def _query_dict(request: Request) -> dict:
    return {key: request.query_params.get(key) for key in request.query_params.keys()}


async def handle_postback(request: Request) -> JSONResponse:
    """GET query postback or POST JSON/form postback. 200 once the row is stored."""
    try:
        raw = await request.body()
        merged = _query_dict(request)
        if request.method.upper() == "POST":
            merged.update(_parse_body(request.headers.get("content-type", ""), raw))
        elif request.method.upper() != "GET":
            raise PostbackError(405, "method_not_allowed", "Use GET or POST.")
        result = record_postback(
            merged,
            raw_body=raw if request.method.upper() == "POST" else b"",
            query_string=request.scope.get("query_string", b""),
            headers=request.headers,
        )
    except PostbackError as exc:
        return JSONResponse(
            {"ok": False, "error": exc.code, "message": exc.message},
            status_code=exc.status,
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse(
        {"ok": True, "status": "accepted", "duplicate": result["duplicate"], "event": result["event"]},
        status_code=200,
        headers={"Cache-Control": "no-store"},
    )

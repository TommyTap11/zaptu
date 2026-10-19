"""Privacy-friendly visit and usage counter (no cookies, no IPs, no third parties).

Unique visitors are counted with sha256(daily_salt + ip + user_agent). The salt is
random, kept only in memory, and rotates every UTC day, so a hash cannot be linked
to a person or across days. Raw IPs and user agents are never written to disk.

Storage: Postgres if DATABASE_URL is set (Supabase-compatible, table
``events``), otherwise SQLite at <data_dir>/analytics.sqlite3 (override with
ZAPTU_ANALYTICS_DB). The SQLite path is only durable on a persistent disk;
Postgres survives Render restarts/redeploys.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from . import config, db

# sha256 of the token in the box secrets file. Env STATS_TOKEN (plain) or
# STATS_TOKEN_SHA256 override it. Only the hash is in the (public) repo.
DEFAULT_STATS_TOKEN_SHA256 = "7e757578a1f5a76b632af55ae252d93bfe45e1429ee8562279c69bb87e57d397"

_LOCK = Lock()
_SALT: dict[str, str] = {}

BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|scrape|headless|phantom|selenium|puppeteer|playwright|lighthouse|"
    r"pagespeed|curl|wget|python-requests|httpx|aiohttp|go-http|java/|okhttp|axios|node-fetch|"
    r"facebookexternalhit|preview|monitor|uptime|pingdom|gptbot|claudebot|perplexitybot|bytespider|"
    r"ccbot|petalbot|semrush|ahrefs|mj12|dotbot|yandex|baidu",
    re.I,
)

AI_HOSTS = {
    "chatgpt.com": "ChatGPT", "chat.openai.com": "ChatGPT", "perplexity.ai": "Perplexity",
    "www.perplexity.ai": "Perplexity", "claude.ai": "Claude", "gemini.google.com": "Gemini",
    "copilot.microsoft.com": "Copilot", "grok.com": "Grok", "x.com": "X", "t.co": "X",
    "you.com": "You.com", "phind.com": "Phind", "chat.deepseek.com": "DeepSeek", "meta.ai": "Meta AI",
}

SITE_HOSTS = {"zaptu.ai", "www.zaptu.ai", "api.zaptu.ai"}
ALLOWED_EVENTS = {"pageview", "call_click"}


def _db_path() -> Path:
    raw = os.getenv("ZAPTU_ANALYTICS_DB")
    return Path(raw) if raw else config.settings.data_dir / "analytics.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=5)
    con.execute(
        "CREATE TABLE IF NOT EXISTS events (day TEXT, ts TEXT, kind TEXT, name TEXT, "
        "referrer TEXT, visitor TEXT)"
    )
    con.execute("CREATE INDEX IF NOT EXISTS events_day ON events(day)")
    return con


# --- Postgres backend (DATABASE_URL set) ---
# Seam for tests: monkeypatch analytics._pg_connect with a fake factory.

def _pg_connect():
    return db.connect_postgres()


_PG_DDL = (
    "CREATE TABLE IF NOT EXISTS events (day TEXT, ts TEXT, kind TEXT, name TEXT, "
    "referrer TEXT, visitor TEXT)",
    "CREATE INDEX IF NOT EXISTS events_day ON events(day)",
)


def _pg_ensure(con) -> None:
    cur = con.cursor()
    for stmt in _PG_DDL:
        cur.execute(stmt)
    con.commit()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def visitor_hash(ip: str, user_agent: str, day: str | None = None) -> str:
    day = day or _today()
    with _LOCK:
        if day not in _SALT:
            _SALT.clear()
            _SALT[day] = secrets.token_hex(16)
        salt = _SALT[day]
    return hashlib.sha256(f"{salt}|{ip}|{user_agent}".encode()).hexdigest()[:16]


def is_bot(user_agent: str | None) -> bool:
    ua = (user_agent or "").strip()
    return not ua or bool(BOT_RE.search(ua))


def classify_referrer(ref: str | None) -> str:
    if not ref:
        return "direct"
    try:
        host = (urlparse(ref).hostname or "").lower()
    except ValueError:
        return "other"
    if not host:
        return "direct"
    if host in SITE_HOSTS:
        return "internal"
    if host in AI_HOSTS:
        return AI_HOSTS[host]
    if host == "google.com" or host.startswith("google.") or ".google." in host or host.endswith(".google.com"):
        return "Google"
    if host.endswith("bing.com"):
        return "Bing"
    if host.endswith("duckduckgo.com"):
        return "DuckDuckGo"
    if host.endswith("yahoo.com"):
        return "Yahoo"
    return host.removeprefix("www.")[:100]


def clean_path(path: str | None) -> str:
    p = (path or "/").split("?")[0].split("#")[0][:200]
    if not p.startswith("/"):
        p = "/" + p
    return p


def _insert(kind: str, name: str, referrer: str = "", visitor: str = "") -> None:
    now = datetime.now(timezone.utc)
    params = (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), kind, name[:200], referrer[:100], visitor)
    try:
        if db.use_postgres():
            con = _pg_connect()
            try:
                _pg_ensure(con)
                cur = con.cursor()
                cur.execute("INSERT INTO events VALUES (%s,%s,%s,%s,%s,%s)", params)
                con.commit()
            finally:
                con.close()
            return
        con = _connect()
        with con:
            con.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", params)
        con.close()
    except Exception:
        pass  # counting must never break the site or API


def record_hit(event: str, path: str, referrer: str | None, ip: str, user_agent: str) -> bool:
    """Returns True if counted, False if filtered (bot / unknown event)."""
    if event not in ALLOWED_EVENTS or is_bot(user_agent):
        return False
    _insert(event, clean_path(path), classify_referrer(referrer), visitor_hash(ip, user_agent))
    return True


def record_api(name: str) -> None:
    _insert("api", name)


def dashboard_pin_ok(pin: str | None) -> bool:
    """Constant-time check of the dashboard PIN against env DASHBOARD_PIN.

    Fail closed: no PIN configured on the server means no access.
    The PIN value lives only in the server environment, never in code/repo.
    """
    want = os.getenv("DASHBOARD_PIN")
    if not want or not pin:
        return False
    return hmac.compare_digest(pin, want)


def token_ok(token: str | None) -> bool:
    if not token:
        return False
    plain = os.getenv("STATS_TOKEN")
    if plain:
        return hmac.compare_digest(token, plain)
    want = os.getenv("STATS_TOKEN_SHA256") or DEFAULT_STATS_TOKEN_SHA256
    return hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), want)


def stats(days: int = 30) -> dict:
    days = max(1, min(days, 366))
    since = (datetime.now(timezone.utc) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    pg = db.use_postgres()
    ph = "%s" if pg else "?"
    if pg:
        con = _pg_connect()
        _pg_ensure(con)

        def q(sql):  # noqa: E306
            cur = con.cursor()
            cur.execute(sql.replace("?", ph), (since,))
            return cur.fetchall()

        def q_one(sql):
            cur = con.cursor()
            cur.execute(sql.replace("?", ph))
            return cur.fetchone()
    else:
        con = _connect()
        q = lambda sql: con.execute(sql, (since,)).fetchall()  # noqa: E731
        q_one = lambda sql: con.execute(sql).fetchone()  # noqa: E731
    per_day = {
        d: {"visits": v, "unique_visitors": u, "call_clicks": 0, "api_calls": 0}
        for d, v, u in q("SELECT day, COUNT(*), COUNT(DISTINCT visitor) FROM events WHERE kind='pageview' AND day>=? GROUP BY day")
    }
    for d, n in q("SELECT day, COUNT(*) FROM events WHERE kind='call_click' AND day>=? GROUP BY day"):
        per_day.setdefault(d, {"visits": 0, "unique_visitors": 0, "call_clicks": 0, "api_calls": 0})["call_clicks"] = n
    for d, n in q("SELECT day, COUNT(*) FROM events WHERE kind='api' AND day>=? GROUP BY day"):
        per_day.setdefault(d, {"visits": 0, "unique_visitors": 0, "call_clicks": 0, "api_calls": 0})["api_calls"] = n
    top = lambda kind, col: [  # noqa: E731
        {"name": n, "count": c}
        for n, c in q(f"SELECT {col}, COUNT(*) c FROM events WHERE kind='{kind}' AND day>=? GROUP BY {col} ORDER BY c DESC LIMIT 25")
    ]
    total = q("SELECT COUNT(*) FROM events WHERE kind='pageview' AND day>=?")[0][0]
    clicks = q("SELECT COUNT(*) FROM events WHERE kind='call_click' AND day>=?")[0][0]
    api = q("SELECT COUNT(*) FROM events WHERE kind='api' AND day>=?")[0][0]
    first = q_one("SELECT MIN(day) FROM events")[0]
    out = {
        "range": {"days": days, "since": since, "timezone": "UTC"},
        "data_since": first,
        "totals": {"visits": total, "call_clicks": clicks, "api_calls": api},
        "per_day": [{"day": d, **v} for d, v in sorted(per_day.items(), reverse=True)],
        "top_pages": top("pageview", "name"),
        "referrers": top("pageview", "referrer"),
        "call_clicks_by_page": top("call_click", "name"),
        "api_by_endpoint": top("api", "name"),
        "notes": "unique_visitors are per day (daily-rotating salted hash); bots filtered by user agent.",
    }
    con.close()
    return out

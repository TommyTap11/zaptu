"""Postgres backend (DATABASE_URL set) with a fake psycopg connection.

No real database: the fake cursor emulates just the SQL the analytics and
lead stores issue. SQLite/JSONL paths are covered here too (no DATABASE_URL).
"""

from __future__ import annotations

import re
import sys
import types

import pytest


# --- fake psycopg -----------------------------------------------------------

class FakeCursor:
    def __init__(self, con):
        self.con = con
        self._result = []

    def execute(self, sql, params=None):
        params = params or ()
        s = " ".join(sql.split())
        self.con.queries.append((s, params))
        if s.startswith(("CREATE TABLE", "CREATE INDEX")):
            self._result = []
        elif s.startswith("INSERT INTO events"):
            self.con.events.append(params)  # (day, ts, kind, name, referrer, visitor)
            self._result = []
        elif s.startswith("INSERT INTO leads"):
            self.con.leads.append(params)  # (id, created_at, payload), append = seq order
            self._result = []
        elif s.startswith("SELECT payload FROM leads WHERE id="):
            self._result = [(p,) for (i, _c, p) in self.con.leads if i == params[0]][:1]
        elif s.startswith("SELECT payload FROM leads ORDER BY seq DESC"):
            rows = list(reversed(self.con.leads))[: params[0]]
            self._result = [(p,) for (_i, _c, p) in rows]
        elif "FROM events" in s:
            self._result = self._events_query(s, params)
        else:  # pragma: no cover
            raise AssertionError(f"unexpected SQL: {s}")

    def _events_query(self, s, params):
        since = params[0] if params else None
        ev = [e for e in self.con.events if since is None or e[0] >= since]
        m = re.search(r"WHERE kind='(\w+)'", s)
        kind = m.group(1) if m else None
        if kind:
            ev = [e for e in ev if e[2] == kind]
        if "SELECT MIN(day)" in s:
            return [(min((e[0] for e in self.con.events), default=None),)]
        if s.startswith("SELECT COUNT(*)"):
            return [(len(ev),)]
        if "GROUP BY day" in s:
            days = {}
            for e in ev:
                days.setdefault(e[0], []).append(e)
            if "COUNT(DISTINCT visitor)" in s:
                return [(d, len(v), len({e[5] for e in v})) for d, v in days.items()]
            return [(d, len(v)) for d, v in days.items()]
        m = re.match(r"SELECT (\w+), COUNT\(\*\)", s)
        if m:  # top-pages / referrers / api breakdown
            idx = {"name": 3, "referrer": 4}[m.group(1)]
            counts = {}
            for e in ev:
                counts[e[idx]] = counts.get(e[idx], 0) + 1
            return sorted(counts.items(), key=lambda kv: -kv[1])[:25]
        raise AssertionError(f"unhandled events SQL: {s}")  # pragma: no cover

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        return self._result[0] if self._result else None


class FakeConnection:
    def __init__(self):
        self.events = []
        self.leads = []
        self.queries = []
        self.commits = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True  # data kept: factory returns this same object


@pytest.fixture()
def fake_pg(monkeypatch):
    con = FakeConnection()
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@pooler.example:6543/postgres")
    from aslc import analytics, storage

    monkeypatch.setattr(analytics, "_pg_connect", lambda: con)
    monkeypatch.setattr(storage, "_pg_connect", lambda: con)
    return con


@pytest.fixture()
def no_pg(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from aslc import config

    config.settings.data_dir = tmp_path
    return tmp_path


def _record(name="Ada Lovelace"):
    from aslc.models import LeadRecord, LeadStatus, ServiceRequest

    req = ServiceRequest(
        service_type="hvac", zip_code="33131", customer_name=name,
        customer_phone="3055550100", consent_to_contact=True, source_agent="test",
    )
    return LeadRecord(request=req, status=LeadStatus.collected)


# --- selection ---------------------------------------------------------------

def test_database_url_selection(monkeypatch):
    from aslc import db

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.database_url() is None and db.use_postgres() is False
    monkeypatch.setenv("DATABASE_URL", "  ")
    assert db.use_postgres() is False
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:6543/db")
    assert db.use_postgres() is True


def test_connect_postgres_uses_psycopg_with_database_url(monkeypatch):
    seen = {}
    fake = types.ModuleType("psycopg")
    def _connect(url):
        seen["url"] = url
        return "CONN"

    fake.connect = _connect
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:6543/db")
    from aslc import db

    assert db.connect_postgres() == "CONN"
    assert seen["url"] == "postgresql://u:p@h:6543/db"


# --- analytics over Postgres --------------------------------------------------

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"


def test_pg_hit_and_stats_shape(fake_pg):
    from aslc import analytics

    assert analytics.record_hit("pageview", "/plumbing/miami-fl/?x=1", "https://www.google.com/", "203.0.113.1", UA)
    assert analytics.record_hit("pageview", "/", "", "203.0.113.2", UA)
    assert analytics.record_hit("call_click", "/plumbing/", "", "203.0.113.1", UA)
    analytics.record_api("/v1/services")
    assert not analytics.record_hit("pageview", "/", "", "1.2.3.4", "Googlebot/2.1")
    # placeholders are Postgres-style, no raw IP/UA persisted
    inserts = [q for q in fake_pg.queries if q[0].startswith("INSERT INTO events")]
    assert inserts and all("%s" in q[0] and "?" not in q[0] for q in inserts)
    assert all("203.0.113.1" not in str(q[1]) and "iPhone" not in str(q[1]) for q in inserts)

    s = analytics.stats(30)
    assert s["totals"] == {"visits": 2, "call_clicks": 1, "api_calls": 1}
    assert s["per_day"][0]["visits"] == 2 and s["per_day"][0]["api_calls"] == 1
    assert {r["name"] for r in s["referrers"]} == {"Google", "direct"}
    assert {r["name"] for r in s["top_pages"]} == {"/", "/plumbing/miami-fl/"}
    assert s["api_by_endpoint"] == [{"name": "/v1/services", "count": 1}]
    assert s["data_since"] is not None


def test_pg_analytics_failure_is_swallowed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    from aslc import analytics

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(analytics, "_pg_connect", boom)
    assert analytics.record_hit("pageview", "/", "", "1.2.3.4", UA) is True  # never breaks the site


# --- leads over Postgres ------------------------------------------------------

def test_pg_lead_roundtrip_and_order(fake_pg):
    from aslc import storage

    a, b = _record("Ada Lovelace"), _record("Grace Hopper")
    storage.append_lead(a)
    storage.append_lead(b)
    assert storage.get_lead(a.id).request.customer_name == "Ada Lovelace"
    assert storage.get_lead("missing") is None
    assert [r.id for r in storage.list_leads()] == [a.id, b.id]  # oldest first, like JSONL
    assert [r.id for r in storage.list_leads(limit=1)] == [b.id]
    inserts = [q for q in fake_pg.queries if q[0].startswith("INSERT INTO leads")]
    assert inserts and all("%s" in q[0] for q in inserts)


def test_pg_lead_failure_is_logged_not_raised(monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    from aslc import storage

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(storage, "_pg_connect", boom)
    storage.append_lead(_record())  # stdout event still emitted; no exception
    assert storage.get_lead("x") is None
    assert storage.list_leads() == []


# --- SQLite / JSONL fallback (no DATABASE_URL) --------------------------------

def test_sqlite_analytics_without_database_url(no_pg):
    from aslc import analytics

    assert analytics.record_hit("pageview", "/", "https://www.bing.com/", "203.0.113.9", UA)
    s = analytics.stats(7)
    assert s["totals"]["visits"] == 1
    assert (no_pg / "analytics.sqlite3").exists()


def test_jsonl_leads_without_database_url(no_pg):
    from aslc import storage

    rec = _record()
    storage.append_lead(rec)
    assert storage.get_lead(rec.id).id == rec.id
    assert [r.id for r in storage.list_leads()] == [rec.id]
    assert (no_pg / "leads.jsonl").exists()

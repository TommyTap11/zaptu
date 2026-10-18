"""Database backend selection.

If DATABASE_URL is set, use Postgres (Supabase-compatible) via psycopg.
Otherwise callers keep their existing local storage (SQLite for analytics,
JSONL for leads) so local runs and tests need no database.

DATABASE_URL is read on every call (not cached) so tests can toggle it
with monkeypatch.setenv/delenv.
"""

from __future__ import annotations

import os
from typing import Any


def database_url() -> str | None:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    return raw or None


def use_postgres() -> bool:
    return database_url() is not None


def connect_postgres() -> Any:
    """Return a new psycopg connection. Imported lazily so SQLite-only
    installs/tests without psycopg still work when DATABASE_URL is unset."""
    import psycopg  # type: ignore[import-not-found]

    return psycopg.connect(database_url())

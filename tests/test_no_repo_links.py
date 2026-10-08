"""The public site must not link to or mention the source repository."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
BANNED = ("github.com", "tommytap11")


def test_no_repo_references_under_web():
    hits = []
    for f in WEB.rglob("*"):  # rglob includes hidden dirs like .well-known
        if not f.is_file() or ".netlify" in f.parts or f.suffix in {".png", ".jpg", ".ico"}:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore").lower()
        hits += [f"{f.relative_to(WEB)}: {b}" for b in BANNED if b in text]
    assert not hits, hits


def test_site_generators_do_not_add_repo_links():
    for name in ("build_plumbing_cities.py", "seo.py"):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8").lower()
        assert not any(b in text for b in BANNED), name

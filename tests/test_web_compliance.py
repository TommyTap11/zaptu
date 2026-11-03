"""Ad-copy rules for every public HTML page (no "free" outside the disclaimer, no prices, superlatives or reviews)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
PAGES = [p for p in sorted(WEB.rglob("*.html")) if "dashboard" not in p.parts]  # private dashboard: see test_dashboard.py
CITY_PAGES = sorted((WEB / "plumbing").glob("*/index.html"))

DISCLAIMER_RE = re.compile(r'<p class="disclaimer">.*?</p>', re.S)
BANNED = [
    r"\bfree\b", r"\bcheap(est)?\b", r"\baffordable\b", r"\blowest\b", r"\bbest\b",
    r"\bmost\b", r"\btop\b", r"#1", r"\bnumber one\b", r"\bfastest\b", r"\blicensed\b",
    r"\binsured\b", r"\bguarantee[sd]?\b", r"\bcertified\b", r"\b24/7\b",
    r"\bin \d+ minutes\b", r"\breviews\b", r"\b(customer|5-star|five-star) review\b", r"\btestimonial", r"\bstars?\b",
    r"\$\d",
]


def visible_text(html: str) -> str:
    html = DISCLAIMER_RE.sub(" ", html)
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_no_banned_copy(page):
    raw = page.read_text(encoding="utf-8")
    text = visible_text(raw)
    # meta/title count too
    metas = " ".join(re.findall(r'content="([^"]*)"', raw)) + " " + " ".join(re.findall(r"<title>(.*?)</title>", raw))
    hay = (text + " " + metas).lower()
    hits = [b for b in BANNED if re.search(b, hay)]
    assert not hits, f"{page}: banned terms {hits}"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_disclaimer_present(page):
    assert 'class="disclaimer"' in page.read_text(encoding="utf-8")


def test_city_pages_exist():
    assert len(CITY_PAGES) >= 10


@pytest.mark.parametrize("page", CITY_PAGES, ids=lambda p: p.parent.name)
def test_city_page_form_and_schema(page):
    raw = page.read_text(encoding="utf-8")
    form = raw[raw.index('<form id="request"'): raw.index("</form>")]
    assert 'action="https://api.zaptu.ai/v1/intake"' in form
    assert '<input type="hidden" name="service_type" value="plumbing" />' in form
    assert "Polyares and its service-provider partners" in form
    # Only call link allowed: the Polyares plumbing tracking number (2026-11-02); see test_plumbing_call_number.py
    assert re.findall(r'href="tel:[^"]*"', raw) == ['href="tel:+18553601813"']
    assert "participating independent plumbing professional" in raw
    assert "not a booking" in raw
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S)
    assert len(blocks) == 1
    data = json.loads(blocks[0])
    types = {n["@type"] for n in data["@graph"]}
    assert types == {"WebPage", "Service", "BreadcrumbList", "FAQPage"}
    assert "LocalBusiness" not in blocks[0]
    assert "address" not in blocks[0]
    assert "aggregateRating" not in blocks[0]
    index = (WEB / "plumbing" / "index.html").read_text(encoding="utf-8")
    assert f'/plumbing/{page.parent.name}/' in index
    assert f'/plumbing/{page.parent.name}/' in (WEB / "sitemap.xml").read_text(encoding="utf-8")
    assert f'/plumbing/{page.parent.name}/' in (WEB / "llms.txt").read_text(encoding="utf-8")


# The Client Connector was dropped on 2026-10-26: no trace of its number or name anywhere we publish.
TCC_MARKERS = ["3085299543", "308-529-9543", "529-9543", "client connector", "get_plumbing_call_number", "call-to-connect", "call to connect"]


def test_no_client_connector_anywhere_in_built_site():
    root = WEB.parent
    files = [p for p in WEB.rglob("*") if p.is_file() and p.suffix in {".html", ".txt", ".json", ".xml", ".js", ".webmanifest", ""}]
    files.append(root / "server.json")
    assert len(files) > 100
    for p in files:
        text = p.read_text(encoding="utf-8", errors="ignore").lower()
        hits = [m for m in TCC_MARKERS if m in text]
        assert not hits, f"{p.relative_to(root)}: {hits}"

"""Client Connector ad-copy rules for every public HTML page."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
PAGES = sorted(WEB.rglob("*.html"))
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
def test_city_page_call_and_schema(page):
    raw = page.read_text(encoding="utf-8")
    assert 'href="tel:+13085299543"' in raw
    assert "(308) 529-9543" in raw
    assert "Call to be connected with a local plumbing professional" in raw
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S)
    assert len(blocks) == 1
    data = json.loads(blocks[0])
    types = {n["@type"] for n in data["@graph"]}
    assert types == {"WebPage", "Service", "BreadcrumbList"}
    assert "LocalBusiness" not in blocks[0]
    assert "address" not in blocks[0]
    assert "aggregateRating" not in blocks[0]
    index = (WEB / "plumbing" / "index.html").read_text(encoding="utf-8")
    assert f'/plumbing/{page.parent.name}/' in index
    assert f'/plumbing/{page.parent.name}/' in (WEB / "sitemap.xml").read_text(encoding="utf-8")
    assert f'/plumbing/{page.parent.name}/' in (WEB / "llms.txt").read_text(encoding="utf-8")

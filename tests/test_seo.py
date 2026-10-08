"""SEO plumbing checks for the static site."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
PAGES = sorted(WEB.rglob("index.html"))
CITY_PAGES = sorted((WEB / "plumbing").glob("*/index.html"))


def url_path(p: Path) -> str:
    rel = p.relative_to(WEB).parent.as_posix()
    return "/" if rel == "." else f"/{rel}/"


def indexable(p: Path) -> bool:
    return 'content="noindex' not in p.read_text(encoding="utf-8")


def test_titles_and_descriptions_unique():
    titles, descs = {}, {}
    for p in PAGES:
        t = p.read_text(encoding="utf-8")
        titles.setdefault(re.search(r"<title>(.*?)</title>", t, re.S).group(1), []).append(p)
        descs.setdefault(re.search(r'<meta name="description" content="([^"]+)"', t).group(1), []).append(p)
    assert all(len(v) == 1 for v in titles.values()), {k: v for k, v in titles.items() if len(v) > 1}
    assert all(len(v) == 1 for v in descs.values())


@pytest.mark.parametrize("page", PAGES, ids=lambda p: url_path(p))
def test_head_tags(page):
    t = page.read_text(encoding="utf-8")
    canon = f"https://zaptu.ai{url_path(page)}"
    assert t.count('<link rel="canonical"') == 1
    assert f'<link rel="canonical" href="{canon}" />' in t
    assert f'<meta property="og:url" content="{canon}" />' in t
    for tag in ("og:title", "og:description", "og:image", "twitter:card", "twitter:title"):
        assert tag in t
    assert len(re.findall(r"<h1[\s>]", t)) == 1
    assert '<meta name="robots"' in t


@pytest.mark.parametrize("page", PAGES, ids=lambda p: url_path(p))
def test_internal_links_use_trailing_slash(page):
    t = page.read_text(encoding="utf-8")
    known = {url_path(p) for p in PAGES}
    for href in re.findall(r'href="(/[^"#]*)', t):
        if href.endswith("/") or "." in href.rsplit("/", 1)[-1]:
            continue
        assert f"{href}/" not in known, f"{page}: {href} should end with /"
    assert 'href="/plumbing/"' in t.split('class="footer-meta"')[1] if 'class="footer-meta"' in t else True


def test_sitemap_and_robots():
    sm = (WEB / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>(.*?)</loc>", sm)
    expected = {f"https://zaptu.ai{url_path(p)}" for p in PAGES if indexable(p)}
    assert set(locs) == expected
    assert sm.count("<lastmod>") == len(locs)
    assert "https://zaptu.ai/thanks/" not in locs
    robots = (WEB / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://zaptu.ai/sitemap.xml" in robots
    assert re.search(r"User-agent: \*\s*\nAllow: /", robots)


def test_indexnow_key_file():
    keys = [p for p in WEB.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}\.txt", p.name)]
    assert len(keys) == 1
    assert keys[0].read_text().strip() == keys[0].stem


def test_home_links_plumbing_and_cities():
    t = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="/plumbing/"' in t
    for p in CITY_PAGES:
        assert f'href="/plumbing/{p.parent.name}/"' in t


@pytest.mark.parametrize("page", CITY_PAGES, ids=lambda p: p.parent.name)
def test_city_breadcrumb_and_siblings(page):
    t = page.read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', t, re.S).group(1))
    crumbs = [n for n in data["@graph"] if n["@type"] == "BreadcrumbList"][0]["itemListElement"]
    assert [c["item"] for c in crumbs] == [
        "https://zaptu.ai/", "https://zaptu.ai/plumbing/", f"https://zaptu.ai/plumbing/{page.parent.name}/",
    ]
    siblings = {s for s in re.findall(r'href="/plumbing/([a-z-]+)/"', t)} - {page.parent.name}
    assert 2 <= len(siblings)
    assert 'href="/plumbing/"' in t

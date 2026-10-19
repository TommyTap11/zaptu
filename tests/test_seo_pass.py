"""Site-wide on-page SEO rules (Oct 19, 2026 pass)."""
import html
import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
SITEMAP = (WEB / "sitemap.xml").read_text()
LOCS = re.findall(r"<loc>https://zaptu\.ai(/[^<]*)</loc>", SITEMAP)
PAGES = [WEB / (p.strip("/") + "/index.html" if p != "/" else "index.html") for p in LOCS]


def lds(text):
    out = []
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
        d = json.loads(m)
        out += d.get("@graph", [d])
    return out


def test_sitemap_lastmod_and_count():
    assert len(LOCS) >= 100
    assert len(LOCS) == len(set(LOCS))
    for lm in re.findall(r"<lastmod>([^<]+)</lastmod>", SITEMAP):
        assert re.fullmatch(r"2026-\d\d-\d\d", lm)
    assert "/dashboard/" not in SITEMAP and "/thanks/" not in SITEMAP


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_on_page(page):
    t = page.read_text()
    title = html.unescape(re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip())
    desc = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', t).group(1))
    assert 15 <= len(title) <= 60, title
    assert 70 <= len(desc) <= 155, desc
    assert len(re.findall(r"<h1\b", t)) == 1
    path = "/" + page.relative_to(WEB).parent.as_posix().strip(".") + "/"
    path = "/" if path == "//" else path
    assert re.findall(r'rel="canonical" href="([^"]+)"', t) == [f"https://zaptu.ai{path}"]
    for tag in ('property="og:title"', 'name="twitter:card"', 'rel="apple-touch-icon"', 'name="viewport"'):
        assert tag in t
    types = [n.get("@type") for n in lds(t)]
    assert not {"LocalBusiness", "AggregateRating", "Review", "Plumber", "HomeAndConstructionBusiness"} & set(types)
    if "FAQPage" in types:
        faq = next(n for n in lds(t) if n["@type"] == "FAQPage")
        for q in faq["mainEntity"]:
            assert html.escape(q["name"], quote=True) in t or q["name"] in t  # visible on the page
    if path.count("/") == 3:  # city page
        assert "BreadcrumbList" in types and "Service" in types
        svc = next(n for n in lds(t) if n["@type"] == "Service")
        assert svc["areaServed"]["@type"] == "City"
    assert "/dashboard" not in t


@pytest.mark.parametrize("cat", ["plumbing", "cleaning", "pest-control", "garage-door"])
def test_hubs_link_every_city(cat):
    hub = (WEB / cat / "index.html").read_text()
    for city in (WEB / cat).glob("*/index.html"):
        assert f'href="/{cat}/{city.parent.name}/"' in hub


def test_same_city_cross_links():
    for city in (WEB / "cleaning").glob("*/index.html"):
        slug = city.parent.name
        t = city.read_text()
        if (WEB / "plumbing" / slug).exists():
            assert f'href="/plumbing/{slug}/"' in t
        if (WEB / "pest-control" / slug).exists():
            assert f'href="/pest-control/{slug}/"' in t
            assert f'href="/cleaning/{slug}/"' in (WEB / "pest-control" / slug / "index.html").read_text()
        p = WEB / "plumbing" / slug / "index.html"
        if p.exists():
            assert f'href="/cleaning/{slug}/"' in p.read_text()


def test_plumbing_pages_name_no_partner():
    for p in (WEB / "plumbing").rglob("index.html"):
        assert "polyares" not in p.read_text().lower()


def test_index_html_variants_redirect():
    r = (WEB / "_redirects").read_text()
    assert "/plumbing/miami-fl/index.html  /plumbing/miami-fl/  301!" in r
    assert "https://zaptuai.netlify.app/*  https://zaptu.ai/:splat  301!" in r
    assert "/dashboard/index.html" not in r

"""Terms of service page (needed as a ToS URL) and the Nov 2 2026 money pages: Houston pest, Tucson plumbing."""
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
TERMS = WEB / "terms" / "index.html"
CONSENT = ("Zaptu may share your details with Polyares and its service-provider partners, and that Polyares, "
           "those partners, or Zaptu may call or text about this request")
PUBLIC = [p for p in sorted(WEB.rglob("index.html")) if "dashboard" not in p.parts] + [WEB / "404.html"]


def text_of(html: str) -> str:
    html = re.sub(r'<p class="disclaimer">.*?</p>', " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_terms_page_says_referral_only_and_no_booking():
    t = text_of(TERMS.read_text(encoding="utf-8"))
    assert "Zaptu does not perform plumbing, cleaning, pest control or any other home-service work" in t
    assert "independent third-party service providers and lead networks" in t
    assert "does not book an appointment" in t
    assert "No callback, visit, arrival time or price is promised" in t
    assert CONSENT in t
    assert "Do not submit a request if you do not want a call or text" in t  # same line as the privacy page
    assert "operated by Construction Irish LLC dba Zaptu" in t


def test_terms_consent_matches_form_consent():
    # The intake form's consent checkbox wording, in second person, must match the terms.
    form = (WEB / "pest-control" / "houston-tx" / "index.html").read_text(encoding="utf-8")
    assert "I agree Zaptu may share my details with Polyares and its service-provider partners, and that Polyares, those partners, or Zaptu may call or text about this request." in form


def test_terms_in_sitemap_and_canonical():
    t = TERMS.read_text(encoding="utf-8")
    assert '<link rel="canonical" href="https://zaptu.ai/terms/" />' in t
    assert "<loc>https://zaptu.ai/terms/</loc>" in (WEB / "sitemap.xml").read_text()
    assert 'href="/privacy/"' in t and 'href="mailto:hello@zaptu.ai"' in t


@pytest.mark.parametrize("page", PUBLIC, ids=lambda p: str(p.relative_to(WEB)))
def test_footer_links_terms(page):
    footer = page.read_text(encoding="utf-8").split('<p class="footer-meta">', 1)[1].split("</p>", 1)[0]
    assert '<a href="/terms/">Terms</a>' in footer


@pytest.mark.parametrize("rel,cat,hub", [
    ("pest-control/houston-tx", 37, "pest-control"),
    ("plumbing/tucson-az", 1, "plumbing"),
])
def test_new_city_pages_have_polyares_form_and_links(rel, cat, hub):
    t = (WEB / rel / "index.html").read_text(encoding="utf-8")
    assert f"leads.polyares.com/?api_key=bcbd33d83d047f182121c2a4404c4853e3f50324&amp;funnel=3&amp;category={cat}&amp;step=1" in t
    assert "It is a contact request, not a booking." in t
    assert 'class="disclaimer"' in t
    assert f"<loc>https://zaptu.ai/{rel}/</loc>" in (WEB / "sitemap.xml").read_text()
    assert f'href="/{rel}/"' in (WEB / hub / "index.html").read_text(encoding="utf-8")
    assert f"https://zaptu.ai/{rel}/" in (WEB / "llms.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("page", PUBLIC, ids=lambda p: str(p.relative_to(WEB)))
def test_footer_links_priority_city_pages(page):
    t = page.read_text(encoding="utf-8")
    areas = re.search(r'<p class="footer-areas">(.*?)</p>', t, re.S)
    assert areas, page
    for href in ("/plumbing/miami-fl/", "/plumbing/tucson-az/", "/pest-control/houston-tx/", "/pest-control/phoenix-az/"):
        assert f'href="{href}"' in areas.group(1)
    for href in re.findall(r'href="(/[^"]+)"', areas.group(1)):
        assert (WEB / href.strip("/") / "index.html").exists(), href


@pytest.mark.parametrize("rel,cat", [("hvac", 8), ("handyman", 9), ("garage-door", 33)] +
                         [(f"garage-door/{p.name}", 33) for p in sorted((WEB / "garage-door").iterdir()) if p.is_dir()])
def test_more_categories_use_polyares_form(rel, cat):
    t = (WEB / rel / "index.html").read_text(encoding="utf-8")
    assert f"&amp;category={cat}&amp;step=1" in t and 'id="polyares-request"' in t
    assert 'class="backup-form"' in t  # our intake form stays below, collapsed


def test_sitemap_lastmod_marks_polyares_form_pages():
    sm = (WEB / "sitemap.xml").read_text()
    for p in WEB.rglob("index.html"):
        if 'id="polyares-request"' in p.read_text(encoding="utf-8"):
            path = p.parent.relative_to(WEB).as_posix()
            assert re.search(rf"<loc>https://zaptu.ai/{re.escape(path)}/</loc><lastmod>2026-11-\d\d</lastmod>", sm), path

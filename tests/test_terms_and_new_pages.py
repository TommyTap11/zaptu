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

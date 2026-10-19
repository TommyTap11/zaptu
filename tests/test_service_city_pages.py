import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
CATS = ("cleaning", "garage-door", "pest-control", "hvac", "handyman")
PAGES = []
for cat in CATS:
    PAGES += sorted((WEB / cat).rglob("index.html"))
SERVICE_TYPES = {
    "cleaning": "house_cleaning",
    "garage-door": "garage_door",
    "pest-control": "pest_control",
    "hvac": "hvac",
    "handyman": "handyman",
}
BANNED = ["529-9543", "13085299543", "tel:", "$", " best ", "fastest", "review", " we ", " our ", " us "]
HUBS = ("hvac", "handyman")


def service_type(page: Path) -> str:
    rel = page.relative_to(WEB).as_posix()
    cat = rel.split("/", 1)[0]
    return SERVICE_TYPES[cat]


def visible_word_count(html: str) -> int:
    """Words outside head, script, and style."""
    html = re.sub(r"<head\b[^>]*>.*?</head>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return len(re.findall(r"[A-Za-z0-9']+", text))


def test_pages_exist():
    # cleaning hub + 5 cities, garage-door hub + 7 cities, pest-control hub + 6 cities, hvac hub, handyman hub
    assert len(PAGES) == 23


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_page_rules(page):
    text = page.read_text()
    assert "This site is a free service to assist homeowners" in text
    assert 'action="https://api.zaptu.ai/v1/intake"' in text
    if page.relative_to(WEB).as_posix().startswith("cleaning/"):
        assert '<select id="service_type" name="service_type">' in text
        for v in ("house_cleaning", "deep_cleaning", "move_in_out_cleaning"):
            assert f'<option value="{v}">' in text
    else:
        assert f'name="service_type" value="{service_type(page)}"' in text
    body = text.split('<p class="disclaimer">')[0].lower()
    for b in BANNED:
        assert b not in body, b
    assert not re.search(r"\bfree\b", body) and "guarantee" not in body
    sitemap = (WEB / "sitemap.xml").read_text()
    path = "/" + page.parent.relative_to(WEB).as_posix() + "/"
    assert f"https://zaptu.ai{path}" in sitemap
    assert f"https://zaptu.ai{path}" in (WEB / "llms.txt").read_text()


@pytest.mark.parametrize("cat", HUBS)
def test_collecting_hubs_are_substantive(cat):
    page = WEB / cat / "index.html"
    text = page.read_text()
    assert visible_word_count(text) >= 400
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S).group(1))
    types = {node["@type"] for node in data["@graph"]}
    assert "FAQPage" in types
    faq = next(node for node in data["@graph"] if node["@type"] == "FAQPage")
    assert 3 <= len(faq["mainEntity"]) <= 4
    assert list((WEB / cat).glob("*/index.html")) == []
    assert "by city" not in text.lower()
    for href in ("/plumbing/", "/garage-door/", "/pest-control/", "/hvac/", "/handyman/", "/how-it-works/"):
        if href == f"/{cat}/":
            continue
        assert f'href="{href}"' in text


def test_home_form_preselects_hvac_and_handyman():
    text = (WEB / "index.html").read_text()
    assert '<option value="hvac">HVAC</option>' in text
    assert '<option value="handyman">Handyman</option>' in text
    assert 'q.get("service")' in text


CLEANING_PEST_NEW = [
    "cleaning/miami-fl", "cleaning/fort-lauderdale-fl", "cleaning/atlanta-ga", "cleaning/dallas-tx",
    "cleaning/phoenix-az", "pest-control/miami-fl", "pest-control/atlanta-ga",
]


@pytest.mark.parametrize("rel", CLEANING_PEST_NEW)
def test_cleaning_pest_pages_contact_request_only(rel):
    text = (WEB / rel / "index.html").read_text()
    body = text.split('<p class="disclaimer">')[0].lower()
    # Same consent wording as the intake (version 2026-10-19-polyares-v1); no Polyares link or redirect yet.
    assert "share my details with polyares and its service-provider partners" in body
    assert "polyares.com" not in text.lower() and "leads.polyares" not in text.lower()
    assert "http-equiv=\"refresh\"" not in text.lower()
    assert "consent_source_page" in text and 'fetch("/"' in text  # source page + Netlify Forms backup
    assert "not a booking" in body
    for b in ("book now", "same day", "same-day", "arrive", "within an hour", "on time", "guarantee", "lowest", "cheap"):
        assert b not in body, b
    assert "zaptu does not" in body


def test_cta_switch_defaults_to_intake():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bsc", WEB.parent / "scripts" / "build_service_cities.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for svc in mod.SERVICES.values():
        assert svc.get("cta", "intake") == "intake"
        assert "hosted_url" not in svc
    hosted = mod.cta_html({"cta": "hosted_link", "hosted_url": "https://example.com/form?a=1&b=2", "label": "House cleaning"}, "Miami", "FL")
    assert 'href="https://example.com/form?a=1&amp;b=2"' in hosted and "<form" not in hosted

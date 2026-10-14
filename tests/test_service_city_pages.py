import json
import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
CATS = ("garage-door", "pest-control", "hvac", "handyman")
PAGES = []
for cat in CATS:
    PAGES += sorted((WEB / cat).rglob("index.html"))
SERVICE_TYPES = {
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
    # garage-door hub + 7 cities, pest-control hub + 4 cities, hvac hub, handyman hub
    assert len(PAGES) == 15


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_page_rules(page):
    text = page.read_text()
    assert "This site is a free service to assist homeowners" in text
    assert 'action="https://api.zaptu.ai/v1/intake"' in text
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

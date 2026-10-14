import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
PAGES = sorted((WEB / "garage-door").rglob("index.html")) + sorted((WEB / "pest-control").rglob("index.html"))
BANNED = ["529-9543", "13085299543", "tel:", "$", " best ", "fastest", "review", " we ", " our ", " us "]


def test_pages_exist():
    assert len(PAGES) == 13


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(WEB)))
def test_page_rules(page):
    text = page.read_text()
    assert "This site is a free service to assist homeowners" in text
    assert 'action="https://api.zaptu.ai/v1/intake"' in text
    st = "garage_door" if "garage-door" in str(page) else "pest_control"
    assert f'name="service_type" value="{st}"' in text
    body = text.split('<p class="disclaimer">')[0].lower()
    for b in BANNED:
        assert b not in body, b
    assert not re.search(r"\bfree\b", body) and "guarantee" not in body
    sitemap = (WEB / "sitemap.xml").read_text()
    path = "/" + page.parent.relative_to(WEB).as_posix() + "/"
    assert f"https://zaptu.ai{path}" in sitemap
    assert f"https://zaptu.ai{path}" in (WEB / "llms.txt").read_text()

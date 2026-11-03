"""Polyares Pest Control tracking number 855-341-9295 (issued 2026-11-03): pest-control pages only."""

from __future__ import annotations

import html as _html
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PHONE = "855-341-9295"
TEL = "tel:+18553419295"
PEST = sorted((WEB / "pest-control").rglob("index.html"))
PLUMBING = sorted((WEB / "plumbing").rglob("index.html"))
PUBLIC = [p for p in sorted(WEB.rglob("*.html")) if "dashboard" not in p.parts]
OTHER = [p for p in PUBLIC if p not in PEST]
CALL_LINE = (f'<p class="call-line">Prefer to call? <a class="btn-call" href="{TEL}">Call {PHONE}</a></p>')
CALL_NOTE = ("The call goes to a Polyares line that passes it to participating independent providers. "
             "A call is a contact request, not a booking.")
BANNED = [r"\bfree\b", r"\$\d", r"\bbest\b", r"\bfastest\b", r"\breviews?\b", r"\bbook(ed)?\b", r"\barriv",
          r"\bminutes?\b", r"\bguarantee", r"\bwithin\b", r"\btoday\b"]


def _bsc():
    spec = importlib.util.spec_from_file_location("_bsc_pest_t", ROOT / "scripts" / "build_service_cities.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _block(raw: str) -> str:
    i = raw.index('<section id="polyares-request"')
    return raw[i: raw.index("</section>", i) + len("</section>")]


def test_pest_pages_count():
    # /pest-control/ hub + 12 city pages (Houston added 2026-11-02)
    assert len(PEST) == 13
    assert (WEB / "pest-control" / "index.html") in PEST
    assert (WEB / "pest-control" / "houston-tx" / "index.html") in PEST


@pytest.mark.parametrize("page", PEST, ids=lambda p: p.parent.name)
def test_pest_page_has_one_call_link_in_polyares_block(page):
    raw = page.read_text(encoding="utf-8")
    assert raw.count(CALL_LINE) == 1
    assert raw.count(CALL_NOTE) == 1
    assert re.findall(r'href="tel:[^"]*"', raw) == [f'href="{TEL}"']
    block = _block(raw)
    assert CALL_LINE in block and CALL_NOTE in block
    assert block.index(CALL_LINE) < block.index("<iframe")
    assert "category=37" in block


@pytest.mark.parametrize("page", PEST, ids=lambda p: p.parent.name)
def test_pest_page_block_matches_generator(page):
    m = _bsc()
    raw = page.read_text(encoding="utf-8")
    hint = re.search(r'<p class="hint">Pest control(?: in the (.*?) area)?\.', _block(raw))
    city = hint.group(1) if hint else None
    expected = m.polyares_html(37, "Pest control", _html.unescape(city) if city else None, PHONE).strip()
    assert _block(raw).strip() == expected


@pytest.mark.parametrize("page", OTHER, ids=lambda p: p.relative_to(WEB).as_posix())
def test_pest_number_not_on_other_pages(page):
    raw = page.read_text(encoding="utf-8")
    assert "855-341-9295" not in raw and "8553419295" not in raw


def test_plumbing_pages_keep_only_plumbing_number():
    for p in PLUMBING:
        assert re.findall(r'href="tel:[^"]*"', p.read_text(encoding="utf-8")) == ['href="tel:+18553601813"'], p


def test_pest_number_not_in_agent_or_text_files():
    for p in [WEB / "llms.txt", WEB / "llms-full.txt", WEB / "openapi.json", WEB / "sitemap.xml", ROOT / "server.json"]:
        assert "8553419295" not in re.sub(r"\D", "", p.read_text(encoding="utf-8")), p.name


def test_pest_call_copy_follows_rules():
    text = re.sub(r"<[^>]+>", " ", CALL_LINE + " " + CALL_NOTE).lower()
    hits = [b for b in BANNED if re.search(b, text.replace("not a booking", ""))]
    assert not hits, hits
    assert "contact request, not a booking" in text


def test_generator_matches_and_is_pest_only():
    m = _bsc()
    assert m.POLYARES_PEST_PHONE == PHONE
    assert m.tel_href(PHONE) == TEL
    assert m.tel_href("+1 (855) 341-9295") == TEL
    assert m.SERVICES["pest-control"]["polyares_phone"] == PHONE
    assert CALL_LINE in m.cta_html(m.SERVICES["pest-control"], "Houston", "TX")
    assert CALL_LINE in m.polyares_html(37, "Pest control", "Houston", PHONE)
    assert "tel:" not in m.polyares_html(37, "Pest control", "Houston")
    for key, s in m.SERVICES.items():
        if key == "pest-control":
            continue
        assert s.get("polyares_phone") != PHONE, key
        assert "tel:" not in m.cta_html(s, None, None), key

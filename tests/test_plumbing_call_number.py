"""Polyares plumbing tracking number 855-360-1813 (issued 2026-11-02): plumbing pages only."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PHONE = "855-360-1813"
TEL = "tel:+18553601813"
PLUMBING = sorted((WEB / "plumbing").rglob("index.html"))
PUBLIC = [p for p in sorted(WEB.rglob("*.html")) if "dashboard" not in p.parts]
OTHER = [p for p in PUBLIC if p not in PLUMBING]
CALL_LINE = (f'<p class="call-line">Prefer to call? <a class="btn-call" href="{TEL}">Call {PHONE}</a></p>')
CALL_NOTE = ("The call goes to a Polyares line that passes it to participating independent providers. "
             "A call is a contact request, not a booking.")
BANNED = [r"\bfree\b", r"\$\d", r"\bbest\b", r"\bfastest\b", r"\breviews?\b", r"\bbook(ed)?\b", r"\barriv",
          r"\bminutes?\b", r"\bguarantee", r"\bwithin\b", r"\btoday\b"]


def _bsc():
    spec = importlib.util.spec_from_file_location("_bsc_t", ROOT / "scripts" / "build_service_cities.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_plumbing_pages_count():
    # /plumbing/ hub + 65 city pages
    assert len(PLUMBING) == 66
    assert (WEB / "plumbing" / "index.html") in PLUMBING


@pytest.mark.parametrize("page", PLUMBING, ids=lambda p: p.parent.name)
def test_plumbing_page_has_one_call_link_in_polyares_block(page):
    raw = page.read_text(encoding="utf-8")
    assert raw.count(CALL_LINE) == 1
    assert raw.count(CALL_NOTE) == 1
    assert re.findall(r'href="tel:[^"]*"', raw) == [f'href="{TEL}"']
    block = raw[raw.index('<section id="polyares-request"'): raw.index("</section>", raw.index('<section id="polyares-request"'))]
    assert CALL_LINE in block and CALL_NOTE in block
    assert block.index(CALL_LINE) < block.index("<iframe")


@pytest.mark.parametrize("page", OTHER, ids=lambda p: p.relative_to(WEB).as_posix())
def test_number_not_on_other_categories(page):
    raw = page.read_text(encoding="utf-8")
    assert "855-360-1813" not in raw and "8553601813" not in raw
    assert "tel:" not in raw


def test_number_not_in_agent_or_text_files():
    for p in [WEB / "llms.txt", WEB / "llms-full.txt", WEB / "openapi.json", WEB / "sitemap.xml", ROOT / "server.json"]:
        assert "8553601813" not in re.sub(r"\D", "", p.read_text(encoding="utf-8")), p.name


def test_call_copy_follows_rules():
    text = re.sub(r"<[^>]+>", " ", CALL_LINE + " " + CALL_NOTE).lower()
    hits = [b for b in BANNED if re.search(b, text.replace("not a booking", ""))]
    assert not hits, hits
    assert "contact request, not a booking" in text


def test_generator_matches_and_is_plumbing_only():
    m = _bsc()
    assert m.POLYARES_PLUMBING_PHONE == PHONE
    assert m.tel_href(PHONE) == TEL
    assert m.tel_href("+1 (855) 360-1813") == TEL
    with pytest.raises(ValueError):
        m.tel_href("360-1813")
    assert CALL_LINE in m.polyares_html(1, "Plumbing", "Miami", PHONE)
    assert "tel:" not in m.polyares_html(1, "Plumbing", "Miami")
    for key, s in m.SERVICES.items():
        assert not s.get("polyares_phone"), key
        assert "tel:" not in m.cta_html(s, None, None), key

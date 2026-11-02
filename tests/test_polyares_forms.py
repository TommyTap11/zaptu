"""Cleaning, pest-control and plumbing pages carry the Polyares hosted form first, with our
/v1/intake form (Netlify Forms backup copy) kept below as a collapsed fallback."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
KEY = "bcbd33d83d047f182121c2a4404c4853e3f50324"
CATS = {"cleaning": 24, "pest-control": 37, "plumbing": 1}


def pages(trade):
    return [p for p in sorted((WEB / trade).rglob("index.html")) if 'id="request"' in p.read_text(encoding="utf-8")]


def test_counts():
    assert len(pages("cleaning")) >= 11 and len(pages("pest-control")) >= 12 and len(pages("plumbing")) >= 60


def test_each_page_has_one_polyares_form_with_right_category_before_backup():
    for trade, cat in CATS.items():
        for p in pages(trade):
            t = p.read_text(encoding="utf-8")
            assert t.count('id="polyares-request"') == 1, p
            srcs = re.findall(r'<iframe class="partner-frame" src="([^"]+)"', t)
            assert srcs == [f"https://leads.polyares.com/?api_key={KEY}&amp;funnel=3&amp;category={cat}&amp;step=1&amp;buttons=btn-primary"], p
            i_poly, i_det, i_form = t.index('id="polyares-request"'), t.index('<details class="backup-form">'), t.index('<form id="request"')
            assert i_poly < i_det < i_form < t.index("</details>"), p
            assert 'class="disclaimer"' in t, p


def test_other_pages_have_no_polyares_iframe():
    for p in WEB.rglob("*.html"):
        if p.parts[len(WEB.parts)] in CATS:
            continue
        assert "leads.polyares.com" not in p.read_text(encoding="utf-8"), p


def test_apply_script_is_idempotent_and_matches_generator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_apf", WEB.parent / "scripts" / "apply_polyares_forms.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for trade, s in m.TRADES.items():
        for p in pages(trade):
            assert m.patch(p.read_text(encoding="utf-8"), s) is None, p

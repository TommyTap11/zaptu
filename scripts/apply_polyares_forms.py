"""Put the Polyares hosted form on existing cleaning, pest-control and plumbing pages in place.

Only the request-form block changes; the rest of each page (frozen SEO copy) is untouched.
Output matches what build_service_cities.cta_html() renders, so a later regeneration agrees.
Idempotent: pages that already carry the Polyares block are skipped.
"""
from __future__ import annotations

import html
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

spec = importlib.util.spec_from_file_location("_bsc", ROOT / "scripts" / "build_service_cities.py")
bsc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bsc)

TRADES = {
    "cleaning": bsc.SERVICES["cleaning"],
    "pest-control": bsc.SERVICES["pest-control"],
    "plumbing": {"label": "Plumbing", "polyares_category": 1},
}
FORM_RE = re.compile(r'    <form id="request" class="request-form" action="https://api\.zaptu\.ai/v1/intake".*?\n    </form>', re.S)
CITY_RE = re.compile(r'<input type="hidden" name="city" value="([^"]*)" />')


def patch(text: str, s: dict) -> str | None:
    if bsc.POLYARES_MARK in text:
        return None
    m = FORM_RE.search(text)
    if not m:
        raise SystemExit("no request form found")
    form = m.group(0)
    c = CITY_RE.search(form)
    city = html.unescape(c.group(1)) if c else None
    block = bsc.polyares_html(s["polyares_category"], s["label"], city) + "\n" + bsc.backup_wrap(form)
    return text[: m.start()] + block + text[m.end():]


def main() -> None:
    n = 0
    for trade, s in TRADES.items():
        for p in sorted((WEB / trade).rglob("index.html")):
            t = p.read_text(encoding="utf-8")
            if 'id="request"' not in t:
                continue
            new = patch(t, s)
            if new is not None:
                p.write_text(new, encoding="utf-8")
                n += 1
    print(f"patched {n} pages")


if __name__ == "__main__":
    main()

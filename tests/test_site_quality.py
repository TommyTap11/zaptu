"""Site-wide quality checks: shared chrome, contact email, icons, links, structured data, copy."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from test_web_compliance import BANNED, DISCLAIMER_RE

WEB = Path(__file__).resolve().parents[1] / "web"
PAGES = sorted(WEB.rglob("index.html")) + [WEB / "404.html"]
CONTACT = "hello@zaptu.ai"


def rel(p: Path) -> str:
    return str(p.relative_to(WEB))


@pytest.mark.parametrize("page", PAGES, ids=rel)
def test_shared_chrome(page):
    t = page.read_text(encoding="utf-8")
    assert '<html lang="en">' in t
    assert 'name="viewport"' in t
    assert re.search(r"<title>[^<]{10,70}</title>", t), "title missing or too long"
    assert re.search(r'<meta name="description" content="[^"]{50,320}"', t)
    assert '<nav aria-label="Main">' in t
    assert f'<a href="mailto:{CONTACT}">Contact</a>' in t.split('class="footer-meta"')[1]
    for tag in ('rel="icon" href="/favicon.ico"', 'href="/favicon.svg"', 'rel="apple-touch-icon"', 'rel="manifest" href="/site.webmanifest"', 'name="theme-color"'):
        assert tag in t, tag
    assert len(re.findall(r"<h1[\s>]", t)) == 1
    assert 'class="disclaimer"' in t
    for img in re.findall(r"<img\b[^>]*>", t):
        assert "alt=" in img


def test_icon_and_manifest_files():
    for name in ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "site.webmanifest", "404.html"):
        assert (WEB / name).exists(), name
    manifest = json.loads((WEB / "site.webmanifest").read_text())
    for icon in manifest["icons"]:
        assert (WEB / icon["src"].lstrip("/")).exists()


def test_404_is_noindex():
    assert 'content="noindex' in (WEB / "404.html").read_text()


def known_targets() -> set[str]:
    out = set()
    for f in WEB.rglob("*"):
        if f.is_file() and ".netlify" not in f.parts:
            r = "/" + f.relative_to(WEB).as_posix()
            out.add(r)
            if f.name == "index.html":
                out.add(r[: -len("index.html")])
    return out


@pytest.mark.parametrize("page", PAGES, ids=rel)
def test_internal_links_resolve(page):
    targets = known_targets()
    t = page.read_text(encoding="utf-8")
    for href in re.findall(r'(?:href|src)="(/[^"]*)"', t):
        path = href.split("#")[0].split("?")[0] or "/"
        assert path in targets, f"{rel(page)} links to missing {href}"


def test_contact_email_everywhere_it_should_be():
    assert f'href="mailto:{CONTACT}"' in (WEB / "privacy" / "index.html").read_text()
    assert f'href="mailto:{CONTACT}"' in (WEB / "agents" / "index.html").read_text()
    assert CONTACT in (WEB / "llms.txt").read_text()
    assert CONTACT in (WEB / "llms-full.txt").read_text()
    assert json.loads((WEB / ".well-known" / "mcp.json").read_text())["contact"] == CONTACT
    assert json.loads((WEB / ".well-known" / "mcp" / "server-card.json").read_text())["contact"] == CONTACT


def jsonld_blocks(t: str) -> list[dict]:
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)]


@pytest.mark.parametrize("page", PAGES, ids=rel)
def test_structured_data_is_valid_and_honest(page):
    t = page.read_text(encoding="utf-8")
    for block in jsonld_blocks(t):  # json.loads raising = invalid
        raw = json.dumps(block)
        for bad in ("LocalBusiness", "aggregateRating", "Review", "address", "telephone", "priceRange"):
            assert bad not in raw, f"{rel(page)}: {bad}"


def test_home_organization_has_email_only():
    data = jsonld_blocks((WEB / "index.html").read_text())[0]
    org = next(n for n in data["@graph"] if n["@type"] == "Organization")
    assert org["email"] == CONTACT
    assert org["url"] == "https://zaptu.ai/"


def test_home_form_is_accessible_and_plumbing_calls():
    t = (WEB / "index.html").read_text()
    form = t[t.index('<form id="request"'): t.index("</form>")]
    assert 'action="https://api.zaptu.ai/v1/intake"' in form
    for fid in ("customer_name", "customer_phone", "zip_code", "service_type", "bedrooms", "notes", "consent_to_contact"):
        assert f'id="{fid}"' in form and f'for="{fid}"' in form, fid
    assert 'value="plumbing"' not in form  # plumbing is a call, not a form lead
    assert 'role="status"' in form
    assert t.count('href="tel:+13085299543"') >= 2


TEXT_FILES = [WEB / "llms.txt", WEB / "llms-full.txt", WEB / "openapi.json", WEB / ".well-known" / "mcp.json",
              WEB / ".well-known" / "mcp" / "server-card.json", WEB / "site.webmanifest"]


@pytest.mark.parametrize("path", TEXT_FILES, ids=rel)
def test_agent_files_follow_copy_rules(path):
    text = DISCLAIMER_RE.sub(" ", path.read_text(encoding="utf-8")).lower()
    hits = [b for b in BANNED if re.search(b, text)]
    assert not hits, f"{rel(path)}: {hits}"
    assert "campaign" not in text and "11864" not in text and "22691" not in text

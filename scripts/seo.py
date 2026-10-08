"""Idempotent SEO pass over web/: canonical, OG/Twitter, internal links, sitemap, robots.

Run after scripts/build_plumbing_cities.py:
    python3 scripts/seo.py
"""

from __future__ import annotations

import html
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
BASE = "https://zaptu.ai"
OG_IMAGE = f"{BASE}/og-image.png"
NOINDEX = {"thanks"}  # path segments that should not be indexed
CONTACT_EMAIL = "hello@zaptu.ai"

NAV = [("/plumbing/", "Plumbing"), ("/how-it-works/", "How it works"), ("/agents/", "For agents")]
FOOTER_LINKS = [
    ("/plumbing/", "Plumbing"),
    ("/how-it-works/", "How it works"),
    ("/agents/", "For agents"),
    ("/privacy/", "Privacy"),
    (f"mailto:{CONTACT_EMAIL}", "Contact"),
]
ICONS = "\n".join(
    [
        "  <!-- seo:icons -->",
        '  <link rel="icon" href="/favicon.ico" sizes="32x32" />',
        '  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />',
        '  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />',
        '  <link rel="manifest" href="/site.webmanifest" />',
        '  <meta name="theme-color" content="#07080b" />',
        "  <!-- /seo:icons -->",
    ]
)

# Pages that lack a description get one here (keyed by URL path).
FALLBACK_DESCRIPTIONS = {
    "/thanks/": "Your Zaptu request was received. Zaptu does not perform the work and this is not a booking.",
}

PAGE_PATHS: list[str] = []


def url_path(page: Path) -> str:
    rel = page.relative_to(WEB).parent.as_posix()
    return "/" if rel == "." else f"/{rel}/"


def attr(s: str) -> str:
    return html.escape(html.unescape(s), quote=True)


def fix_internal_links(text: str, known: set[str]) -> str:
    # /cleaning -> /cleaning/ (Netlify 301s the slashless form); keep files and anchors as-is.
    def repl(m: re.Match) -> str:
        href = m.group(1)
        path, _, frag = href.partition("#")
        if path and not path.endswith("/") and f"{path}/" in known:
            path = f"{path}/"
        if href == "/#":
            return 'href="/#request"'
        return f'href="{path}{("#" + frag) if frag else ""}"'

    return re.sub(r'href="(/[^"]*)"', repl, text)


def header_html(current: str) -> str:
    links = "\n".join(
        f'      <a href="{href}"' + (' aria-current="page"' if href == current else "") + f">{label}</a>"
        for href, label in NAV
    )
    return f'<header>\n    <a class="brand" href="/">Zaptu</a>\n    <nav aria-label="Main">\n{links}\n    </nav>\n  </header>'


def footer_meta_html() -> str:
    return '<p class="footer-meta">Zaptu · ' + " · ".join(f'<a href="{h}">{t}</a>' for h, t in FOOTER_LINKS) + "</p>"


def apply_chrome(text: str, current: str) -> str:
    """Shared header nav, footer links, and icon/manifest tags on every page."""
    if "<header>" in text:
        text = re.sub(r"<header>.*?</header>", lambda _m: header_html(current), text, count=1, flags=re.S)
    else:
        text = text.replace("<body>\n", "<body>\n  " + header_html(current) + "\n", 1)
    text = re.sub(r'<p class="footer-meta">.*?</p>', lambda _m: footer_meta_html(), text, count=1, flags=re.S)
    text = re.sub(r"\n  <!-- seo:icons -->.*?<!-- /seo:icons -->", "", text, flags=re.S)
    text = text.replace('  <link rel="stylesheet" href="/style.css" />', ICONS + '\n  <link rel="stylesheet" href="/style.css" />', 1)
    return text


def process(page: Path, known: set[str]) -> None:
    text = page.read_text(encoding="utf-8")
    path = url_path(page)
    canonical = f"{BASE}{path}"

    # canonical
    if '<link rel="canonical"' in text:
        text = re.sub(r'<link rel="canonical" href="[^"]*" />', f'<link rel="canonical" href="{canonical}" />', text)
    else:
        text = text.replace("</title>", f'</title>\n  <link rel="canonical" href="{canonical}" />', 1)

    # description
    if '<meta name="description"' not in text:
        desc = FALLBACK_DESCRIPTIONS.get(path, "Zaptu connects people with independent local contractors.")
        text = text.replace("</title>", f'</title>\n  <meta name="description" content="{attr(desc)}" />', 1)

    # robots
    noindex = any(seg in NOINDEX for seg in path.strip("/").split("/"))
    robots = "noindex,follow" if noindex else "index,follow"
    if '<meta name="robots"' in text:
        text = re.sub(r'<meta name="robots" content="[^"]*" />', f'<meta name="robots" content="{robots}" />', text)
    else:
        text = text.replace('<link rel="canonical"', f'<meta name="robots" content="{robots}" />\n  <link rel="canonical"', 1)

    title = re.search(r"<title>(.*?)</title>", text, re.S).group(1).strip()
    desc = re.search(r'<meta name="description" content="([^"]*)"', text).group(1)

    og = "\n".join(
        [
            "  <!-- seo:og -->",
            '  <meta property="og:type" content="website" />',
            '  <meta property="og:site_name" content="Zaptu" />',
            f'  <meta property="og:title" content="{attr(title)}" />',
            f'  <meta property="og:description" content="{desc}" />',
            f'  <meta property="og:url" content="{canonical}" />',
            f'  <meta property="og:image" content="{OG_IMAGE}" />',
            '  <meta property="og:image:width" content="1200" />',
            '  <meta property="og:image:height" content="630" />',
            '  <meta name="twitter:card" content="summary_large_image" />',
            f'  <meta name="twitter:title" content="{attr(title)}" />',
            f'  <meta name="twitter:description" content="{desc}" />',
            f'  <meta name="twitter:image" content="{OG_IMAGE}" />',
            "  <!-- /seo:og -->",
        ]
    )
    text = re.sub(r"\n  <!-- seo:og -->.*?<!-- /seo:og -->", "", text, flags=re.S)
    text = re.sub(r'(<link rel="canonical" href="[^"]*" />)', r"\1\n" + og.replace("\\", "\\\\"), text, count=1)

    text = fix_internal_links(text, known)
    text = apply_chrome(text, path)

    # footer link to /plumbing/
    if 'class="footer-meta"' in text and 'href="/plumbing/">Plumbing</a>' not in text.split('class="footer-meta"')[1]:
        text = text.replace('<p class="footer-meta">Zaptu · ', '<p class="footer-meta">Zaptu · <a href="/plumbing/">Plumbing</a> · ', 1)

    page.write_text(text, encoding="utf-8")


def lastmod(page: Path) -> str:
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(page)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        return date.today().isoformat()
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(page)], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return out or date.today().isoformat()


def main() -> None:
    pages = sorted(WEB.rglob("index.html"))
    known = {url_path(p) for p in pages}
    for p in pages:
        process(p, known)
    not_found = WEB / "404.html"
    if not_found.exists():
        not_found.write_text(apply_chrome(not_found.read_text(encoding="utf-8"), ""), encoding="utf-8")

    entries = []
    for p in pages:
        path = url_path(p)
        if any(seg in NOINDEX for seg in path.strip("/").split("/")):
            continue
        prio = "1.0" if path == "/" else ("0.9" if path == "/plumbing/" else ("0.8" if path.startswith("/plumbing/") else "0.5"))
        entries.append(
            f"  <url><loc>{BASE}{path}</loc><lastmod>{lastmod(p)}</lastmod><priority>{prio}</priority></url>"
        )
    (WEB / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n",
        encoding="utf-8",
    )
    print(f"sitemap.xml: {len(entries)} URLs; processed {len(pages)} pages")


if __name__ == "__main__":
    main()

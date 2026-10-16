import html, json, re
from pathlib import Path
import pytest

WEB = Path(__file__).resolve().parents[1] / "web"
PAGES = sorted((WEB / "plumbing").glob("*/index.html"))


def blocks(t):
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)]


def test_48_city_pages():
    assert len(PAGES) >= 48


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.parent.name)
def test_city_seo(page):
    t = page.read_text()
    title = html.unescape(re.search(r"<title>(.*?)</title>", t).group(1))
    assert title.startswith("Plumber in ") and len(title) <= 65
    desc = re.search(r'<meta name="description" content="([^"]*)"', t).group(1)
    assert len(desc) <= 160 and "does not do the work" in desc
    for h in ("What to tell the plumber", "When to call right away", "plumbing questions"):
        assert h in t
    faq = [n for b in blocks(t) for n in b.get("@graph", []) if n.get("@type") == "FAQPage"]
    assert len(faq) == 1 and len(faq[0]["mainEntity"]) == 5
    for q in faq[0]["mainEntity"]:  # schema must match visible text
        assert q["name"].replace("'", "&#x27;") in t
    assert '<p class="disclaimer">' in t


def test_titles_and_faqs_unique():
    titles = [re.search(r"<title>(.*?)</title>", p.read_text()).group(1) for p in PAGES]
    assert len(set(titles)) == len(titles)
    answers = [re.findall(r'"text": "([^"]*)"', p.read_text())[1] for p in PAGES]
    assert len(set(answers)) == len(answers)

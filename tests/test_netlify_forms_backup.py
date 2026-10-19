"""Every request form also posts a backup copy to Netlify Forms, client-side, without changing the intake post."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def form_pages():
    return [p for p in WEB.rglob("index.html") if 'id="request"' in p.read_text(encoding="utf-8")]


def test_has_form_pages():
    assert len(form_pages()) >= 10


def test_each_form_page_posts_backup_to_netlify():
    for p in form_pages():
        t = p.read_text(encoding="utf-8")
        assert 'action="https://api.zaptu.ai/v1/intake"' in t, p
        assert 'name="bot-field"' in t, p
        assert 'fetch("/", { method: "POST"' in t, p
        assert '"Content-Type": "application/x-www-form-urlencoded"' in t, p
        assert 'nb.set("form-name", "service-request")' in t, p
        assert "keepalive: true" in t, p
        assert "if (!data.dry_run)" in t, p
        # intake post unchanged: still JSON to the form action
        assert 'fetch(f.action, { method: "POST", headers: { "Content-Type": "application/json"' in t, p
        assert t.index('fetch("/"') < t.index("fetch(f.action"), p


def test_netlify_detection_form_on_home():
    t = (WEB / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<form name="service-request" netlify netlify-honeypot="bot-field" hidden>(.*?)</form>', t, re.S)
    assert m
    for field in ["form-name", "bot-field", "customer_name", "customer_phone", "zip_code",
                  "service_type", "city", "state", "bedrooms", "notes", "consent_to_contact", "consent_source_page"]:
        assert f'name="{field}"' in m.group(1), field

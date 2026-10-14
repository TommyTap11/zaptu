"""Build /garage-door/ and /pest-control/ hub + city pages (request form, no phone number).

No buyer phone numbers exist for these categories, so pages use the request form only and must
never show the plumbing tracking number. Copy rules (The Client Connector, applied site-wide):
no "free" outside the approved disclaimer, no prices, no superlatives, no guarantees or reviews,
never imply Zaptu does the work, and no first-person wording that sounds like the provider.

    python3 scripts/build_service_cities.py && python3 scripts/seo.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
BASE = "https://zaptu.ai"

DISCLAIMER = (
    "This site is a free service to assist homeowners in connecting with local service "
    "contractors. All contractors are independent and this site does not warrant or "
    "guarantee any work performed. It is the responsibility of the homeowner to verify "
    "that the hired contractor furnishes the necessary license and insurance required "
    "for the work being performed. All persons depicted in a photo or video are actors "
    "or models and not contractors listed on this site."
)

CITIES = {
    "phoenix-az": ("Phoenix", "AZ", "Arizona"),
    "dallas-tx": ("Dallas", "TX", "Texas"),
    "fort-worth-tx": ("Fort Worth", "TX", "Texas"),
    "san-antonio-tx": ("San Antonio", "TX", "Texas"),
    "atlanta-ga": ("Atlanta", "GA", "Georgia"),
    "kansas-city-mo": ("Kansas City", "MO", "Missouri"),
    "oklahoma-city-ok": ("Oklahoma City", "OK", "Oklahoma"),
}

SERVICES = {
    "garage-door": {
        "service_type": "garage_door",
        "label": "Garage door repair",
        "h1": "Garage door repair in {name}",
        "title": "Garage Door Repair in {name} — Send a Request | Zaptu",
        "desc": "Need garage door repair in {name}? Send a request to be connected with an independent local garage door professional. Zaptu does not perform the work.",
        "hub_title": "Garage door repair — send a request | Zaptu",
        "hub_desc": "Send a request to be connected with an independent local garage door professional. Zaptu does not perform the work and does not book appointments.",
        "hub_lede": "Broken spring, stuck door, or an opener that quit? Send a request to be connected with an independent local garage door professional. A request is not a booking. Zaptu does not perform garage door work.",
        "issues": [
            ("Broken springs", "A loud bang from the garage, a door that suddenly feels very heavy, or a gap in the spring above the door. Springs hold a lot of tension, so leave them alone."),
            ("Door off track or stuck", "A door that hangs crooked, binds partway, or has a roller out of its track. Stop using it so it does not fall."),
            ("Opener problems", "The motor runs but the door does not move, the remote or keypad stopped working, or the door reverses on its own."),
            ("Cables, rollers and hinges", "Frayed cables, worn or noisy rollers, and cracked hinges or brackets."),
            ("Panels and seals", "Dented or cracked panels and worn bottom seals that let in water, dust or pests."),
        ],
        "safety": [
            "Do not try to adjust or release torsion springs or the cables attached to them.",
            "If the door is stuck open, keep people and pets out from under it.",
            "If the door is off its track, unplug the opener so it cannot be run by mistake.",
        ],
        "cities": ["phoenix-az", "dallas-tx", "fort-worth-tx", "san-antonio-tx", "atlanta-ga", "kansas-city-mo", "oklahoma-city-ok"],
        "local": {
            "phoenix-az": ("Phoenix summers push garage temperatures very high, which is hard on opener motors, weather seals, and the lubricant on moving parts.",
                           ["Extreme heat can dry out and crack bottom seals, letting in dust from monsoon storms.",
                            "Many Valley homes use the garage as the main entry, so a stuck door can block daily routines. Mention whether a car is trapped inside."]),
            "dallas-tx": ("Dallas homes often rely on attached garages, and North Texas weather swings from summer heat to the occasional hard freeze.",
                          ["Clay soil movement can shift a slab slightly over time, which can leave a door uneven at the floor.",
                           "Hail season can dent steel panels. Note any storm damage when you describe the problem."]),
            "fort-worth-tx": ("Fort Worth's hot summers and spring storms both take a toll on garage doors, openers and seals.",
                              ["Spring hail can dent panels and damage window inserts in the door.",
                               "Heat can make an older opener struggle. Mention if the door stops and reverses partway."]),
            "san-antonio-tx": ("In San Antonio, long hot seasons and heavy use mean springs, rollers and openers wear over time.",
                               ["Heavy rain can wash debris under the door and wear the bottom seal.",
                                "If the door makes grinding or popping sounds, describe them when someone follows up."]),
            "atlanta-ga": ("Atlanta's humidity and frequent rain can wear on garage door hardware and seals.",
                           ["Moisture can lead to rust on springs, cables and tracks over time.",
                            "Sloped driveways are common, so mention whether the door closes unevenly against the floor."]),
            "kansas-city-mo": ("Kansas City winters bring freezing temperatures that can stiffen moving parts and freeze the bottom seal to the floor.",
                               ["Cold weather is a common time for worn springs to fail.",
                                "If the door is frozen to the ground, avoid forcing it with the opener."]),
            "oklahoma-city-ok": ("Oklahoma City sees strong winds, hail and cold snaps, all of which can affect a garage door.",
                                 ["High winds can bend panels or push a door off its track.",
                                  "After a hail storm, note any dents or cracked panels in your request."]),
        },
        "siblings_label": "Garage door repair in",
    },
    "pest-control": {
        "service_type": "pest_control",
        "label": "Pest control",
        "h1": "Pest control in {name}",
        "title": "Pest Control in {name} — Send a Request | Zaptu",
        "desc": "Need pest control in {name}? Send a request to be connected with an independent local pest control professional. Zaptu does not perform the work.",
        "hub_title": "Pest control — send a request | Zaptu",
        "hub_desc": "Send a request to be connected with an independent local pest control professional. Zaptu does not perform the work and does not book appointments.",
        "hub_lede": "Seeing ants, roaches, rodents or other pests? Send a request to be connected with an independent local pest control professional. A request is not a booking. Zaptu does not perform pest control.",
        "issues": [
            ("Ants and roaches", "Trails in the kitchen or bathroom, or roaches seen at night."),
            ("Rodents", "Droppings, gnaw marks, or scratching sounds in walls or the attic."),
            ("Termites", "Mud tubes on the foundation, swarming winged insects, or soft or hollow-sounding wood."),
            ("Scorpions, spiders and other insects", "Pests coming in from the yard, under doors, or through gaps."),
            ("Mosquitoes and wasps", "Nests near entries, eaves or play areas, and standing water in the yard."),
        ],
        "safety": [
            "Keep children and pets away from any product you have already put down.",
            "Note where and when you see pests; it helps whoever follows up.",
            "If someone is stung and has trouble breathing, call 911.",
        ],
        "cities": ["phoenix-az", "dallas-tx", "fort-worth-tx", "san-antonio-tx"],
        "local": {
            "phoenix-az": ("Phoenix's desert climate brings pests that many other cities rarely see, such as scorpions, along with roaches and termites.",
                           ["Scorpions often come in through gaps under doors and around plumbing. Mention where you have seen them.",
                            "Desert subterranean termites are present in the Valley, so note any mud tubes on walls or the foundation."]),
            "dallas-tx": ("Dallas's warm climate means ants, roaches, termites and mosquitoes are active for much of the year.",
                          ["Fire ants are common in North Texas yards. Note whether mounds are near walkways or play areas.",
                           "Heavy rain can drive ants indoors. Say whether the problem started after a storm."]),
            "fort-worth-tx": ("Fort Worth homes see many of the same pests as the rest of North Texas, from fire ants to termites and rodents in cooler months.",
                              ["Rodents often look for shelter indoors when the weather turns cold.",
                               "Termite swarms in spring are a common reason homeowners reach out."]),
            "san-antonio-tx": ("San Antonio's heat and humidity support a long pest season, including roaches, ants, termites and mosquitoes.",
                               ["Standing water after rain can increase mosquitoes around the home.",
                                "Note whether you see pests mainly inside, in the yard, or both."]),
        },
        "siblings_label": "Pest control in",
    },
}


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def form_html(service_type: str, label: str, city: str | None, abbr: str | None) -> str:
    where = f" in the {esc(city)} area" if city else ""
    city_fields = (
        f'      <input type="hidden" name="city" value="{esc(city)}" />\n      <input type="hidden" name="state" value="{abbr}" />\n'
        if city else ""
    )
    return f"""    <form id="request" class="request-form" action="https://api.zaptu.ai/v1/intake" method="post" name="service-request">
      <p class="hp" aria-hidden="true"><label>Do not fill <input name="bot-field" tabindex="-1" autocomplete="off" /></label></p>
      <h2>Send a request</h2>
      <p class="hint">{esc(label)}{where}. Your request is passed along when a participating provider covers your ZIP code. It is not a booking.</p>
      <input type="hidden" name="service_type" value="{service_type}" />
{city_fields}      <label for="customer_name">Name</label>
      <input id="customer_name" name="customer_name" required minlength="2" maxlength="120" autocomplete="name" />
      <div class="row">
        <div>
          <label for="customer_phone">Phone</label>
          <input id="customer_phone" name="customer_phone" type="tel" required minlength="10" autocomplete="tel-national" inputmode="tel" />
        </div>
        <div>
          <label for="zip_code">ZIP</label>
          <input id="zip_code" name="zip_code" required pattern="[0-9]{{5}}" maxlength="5" inputmode="numeric" autocomplete="postal-code" />
        </div>
      </div>
      <label for="notes">What is going on?</label>
      <textarea id="notes" name="notes" rows="3" maxlength="2000"></textarea>
      <label class="consent" for="consent_to_contact"><input type="checkbox" id="consent_to_contact" name="consent_to_contact" value="yes" required /><span>I agree a provider or Zaptu partner may call or text about this request.</span></label>
      <button type="submit">Send request</button>
      <p id="form-status" class="form-status" role="status" aria-live="polite"></p>
      <p class="note">US residential. <a href="/privacy/">Privacy</a></p>
    </form>"""


FORM_JS = """  <script>
(function () {
  var f = document.getElementById("request");
  if (!f || !window.fetch || !window.URLSearchParams) return;
  var q = new URLSearchParams(location.search), st = document.getElementById("form-status");
  f.addEventListener("submit", function (e) {
    e.preventDefault();
    var data = {};
    new FormData(f).forEach(function (v, k) { data[k] = v; });
    data.consent_to_contact = f.consent_to_contact.checked;
    if (q.get("dry_run") === "1") data.dry_run = true;
    var btn = f.querySelector("button[type=submit]");
    btn.disabled = true; st.textContent = "Sending...";
    [].forEach.call(f.querySelectorAll("[aria-invalid]"), function (el) { el.removeAttribute("aria-invalid"); });
    fetch(f.action, { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" }, body: JSON.stringify(data) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (x) {
        if (x.ok && x.j.status !== "rejected") { location.href = "/thanks/"; return; }
        var fields = (x.j && x.j.fields) || {};
        Object.keys(fields).forEach(function (k) { if (f[k] && f[k].setAttribute) f[k].setAttribute("aria-invalid", "true"); });
        st.textContent = (x.j && x.j.message) || "Something went wrong. Please try again.";
        btn.disabled = false;
      })
      .catch(function () {
        if (data.dry_run) { var h = document.createElement("input"); h.type = "hidden"; h.name = "dry_run"; h.value = "1"; f.appendChild(h); }
        st.textContent = "Sending..."; f.submit();
      });
  });
})();
  </script>"""


def page(title: str, desc: str, url: str, body: str, ld: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  <meta name="robots" content="index,follow" />
  <link rel="stylesheet" href="/style.css" />
  <script type="application/ld+json">
{json.dumps(ld, indent=2)}
  </script>
</head>
<body>
  <header>
    <a class="brand" href="/">Zaptu</a>
  </header>
{body}
  <footer>
    <p class="disclaimer">{DISCLAIMER}</p>
    <p class="footer-meta">Zaptu</p>
  </footer>
{FORM_JS}
</body>
</html>
"""


def crumbs(items: list[tuple[str, str]]) -> dict:
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def city_page(cat: str, s: dict, slug: str) -> str:
    city, abbr, state = CITIES[slug]
    name = f"{city}, {abbr}"
    url = f"{BASE}/{cat}/{slug}/"
    title, desc = s["title"].format(name=name), s["desc"].format(name=name)
    intro, notes = s["local"][slug]
    issues = "\n".join(f"        <li><strong>{esc(t)}.</strong> {esc(d)}</li>" for t, d in s["issues"])
    notes_html = "\n".join(f"        <li>{esc(n)}</li>" for n in notes)
    safety = "\n".join(f"        <li>{esc(n)}</li>" for n in s["safety"])
    sibs = "\n".join(
        f'        <li><a href="/{cat}/{o}/">{s["siblings_label"]} {esc(CITIES[o][0])}, {CITIES[o][1]}</a></li>'
        for o in s["cities"] if o != slug)
    other = [c for c in SERVICES if c != cat and slug in SERVICES[c]["cities"]]
    other_html = "".join(f' · <a href="/{c}/{slug}/">{SERVICES[c]["label"]} in {esc(city)}</a>' for c in other)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc,
         "isPartOf": {"@type": "WebSite", "name": "Zaptu", "url": f"{BASE}/"}},
        {"@type": "Service", "name": f"{s['label']} request referral in {name}",
         "serviceType": f"Referral connecting homeowners with independent local {s['label'].lower()} professionals",
         "description": f"Zaptu passes requests along to participating independent {s['label'].lower()} professionals. Zaptu does not perform the work.",
         "provider": {"@type": "Organization", "name": "Zaptu", "url": f"{BASE}/"},
         "areaServed": {"@type": "City", "name": city, "containedInPlace": {"@type": "State", "name": state}}, "url": url},
        crumbs([("Zaptu", f"{BASE}/"), (s["label"], f"{BASE}/{cat}/"), (name, url)]),
    ]}
    body = f"""  <main class="city">
    <p class="eyebrow"><a href="/{cat}/">{s['label']}</a> / {esc(name)}</p>
    <h1>{esc(s['h1'].format(name=name))}</h1>
    <p class="lede">{esc(intro)} Send a request to be connected with an independent local {s['label'].lower()} professional in the {esc(city)} area.</p>
{form_html(s['service_type'], s['label'], city, abbr)}

    <section>
      <h2>Common reasons people reach out</h2>
      <ul>
{issues}
      </ul>
    </section>

    <section>
      <h2>Things to know in {esc(city)}</h2>
      <ul>
{notes_html}
      </ul>
    </section>

    <section>
      <h2>What happens after you send a request</h2>
      <ol>
        <li>Zaptu records your request and passes it along when a participating independent provider covers your ZIP code.</li>
        <li>If a provider takes the request, they contact you by phone or text to talk through the problem.</li>
        <li>You and the provider agree on timing, the work, and any costs directly. Zaptu is not part of that agreement.</li>
      </ol>
      <p>A request is not a booking, and a callback is not promised. Zaptu does not perform the work and does not send a named company.</p>
    </section>

    <section>
      <h2>Before someone follows up</h2>
      <ul>
{safety}
      </ul>
    </section>

    <section>
      <h2>{s['label']} in other cities</h2>
      <ul class="city-links">
{sibs}
      </ul>
    </section>
    <p class="note"><a href="/{cat}/">All {s['label'].lower()} locations</a>{other_html}</p>
  </main>"""
    return page(title, desc, url, body, ld)


def hub_page(cat: str, s: dict) -> str:
    url = f"{BASE}/{cat}/"
    links = "\n".join(
        f'        <li><a href="/{cat}/{o}/">{s["siblings_label"]} {esc(CITIES[o][0])}, {CITIES[o][1]}</a></li>'
        for o in sorted(s["cities"], key=lambda o: CITIES[o][0]))
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url, "url": url, "name": s["hub_title"], "description": s["hub_desc"],
         "isPartOf": {"@type": "WebSite", "name": "Zaptu", "url": f"{BASE}/"}},
        crumbs([("Zaptu", f"{BASE}/"), (s["label"], url)])]}
    body = f"""  <main>
    <h1>{s['label']}</h1>
    <p class="lede">{esc(s['hub_lede'])}</p>
{form_html(s['service_type'], s['label'], None, None)}
    <section>
      <h2>{s['label']} by city</h2>
      <ul class="city-links">
{links}
      </ul>
    </section>
  </main>"""
    return page(s["hub_title"], s["hub_desc"], url, body, ld)


def main() -> None:
    llms_lines = []
    for cat, s in SERVICES.items():
        (WEB / cat).mkdir(exist_ok=True)
        (WEB / cat / "index.html").write_text(hub_page(cat, s), encoding="utf-8")
        llms_lines.append(f"\n## {s['label']} city pages\nRequest form only (service_type {s['service_type']}, collecting); no phone number.")
        llms_lines.append(f"- [{s['label']}]({BASE}/{cat}/)")
        for slug in s["cities"]:
            out = WEB / cat / slug / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(city_page(cat, s, slug), encoding="utf-8")
            print("wrote", out.relative_to(ROOT))
            c = CITIES[slug]
            llms_lines.append(f"- [{s['siblings_label']} {c[0]}, {c[1]}]({BASE}/{cat}/{slug}/)")
    llms = WEB / "llms.txt"
    text = llms.read_text(encoding="utf-8")
    start, end = "<!-- services:start -->", "<!-- services:end -->"
    block = start + "\n".join(llms_lines) + "\n" + end
    if start in text:
        text = text[: text.index(start)] + block + text[text.index(end) + len(end):]
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    llms.write_text(text, encoding="utf-8")
    print("updated web/llms.txt")


if __name__ == "__main__":
    main()

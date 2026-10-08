"""Build /plumbing/<slug>/ city pages from scripts/plumbing_cities.json.

Copy rules (The Client Connector): no "free" outside the approved disclaimer, no prices,
no superlatives, no reviews, no licensed/insured/guaranteed/response-time claims, never
imply Zaptu does the work or that a named company is coming.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DATA = json.loads((Path(__file__).with_name("plumbing_cities.json")).read_text())

PHONE_DISPLAY = "(308) 529-9543"
PHONE_TEL = "tel:+13085299543"
DISCLAIMER = (
    "This site is a free service to assist homeowners in connecting with local service "
    "contractors. All contractors are independent and this site does not warrant or "
    "guarantee any work performed. It is the responsibility of the homeowner to verify "
    "that the hired contractor furnishes the necessary license and insurance required "
    "for the work being performed. All persons depicted in a photo or video are actors "
    "or models and not contractors listed on this site."
)

# City-specific copy. Hedged, general knowledge only; no stats, no named companies.
LOCAL = {
    "miami-fl": {
        "intro": "Miami has everything from older single-family homes to high-rise condos, and a plumbing problem in a tower is handled differently from one in a house. Call to be connected with a local plumbing professional who can talk through what you are seeing.",
        "notes": [
            "In a condo or apartment, a leak can reach the unit below. Check whether your building management or association needs to know before work starts.",
            "Heavy rain can overwhelm drains. If water is coming up through a floor drain or shower, stop running water until the line is checked.",
            "Humid, salty air can wear on exposed fittings and outdoor hose bibs over time, so mention any corrosion you notice.",
        ],
        "focus": "clogs and drain backups after storms, leaks in condo units, and water heater problems",
    },
    "fort-lauderdale-fl": {
        "intro": "Fort Lauderdale homes sit in a low, wet landscape crossed by canals, which makes drainage and sewer problems a common reason people pick up the phone. Call to be connected with a local plumbing professional.",
        "notes": [
            "Some older properties in Broward County still use septic systems. Say whether you are on septic or city sewer when you call.",
            "After heavy rain, slow drains throughout the house can point to a main line issue rather than a single clog.",
            "Outdoor pipes and fittings near the water can corrode, so mention rust or green buildup on visible lines.",
        ],
        "focus": "sewer and septic questions, slow drains after rain, and leaking fixtures",
    },
    "denver-co": {
        "intro": "Denver's cold snaps are hard on pipes, especially in exterior walls, crawl spaces, and garages. If you have a leak, a frozen line, or a water heater that quit, call to be connected with a local plumbing professional.",
        "notes": [
            "When temperatures fall below freezing, disconnect garden hoses and know where your main shutoff valve is before a pipe splits.",
            "A frozen pipe that thaws can start leaking hours later. Watch ceilings and walls near the line once it warms up.",
            "Water heaters work harder in winter; no hot water or a pilot that keeps going out is worth describing in detail on the call.",
        ],
        "focus": "frozen or burst pipes, water heater outages, and leaks in basements and crawl spaces",
    },
    "atlanta-ga": {
        "intro": "Atlanta's tree cover is part of the city's character, and those same roots can work their way into sewer lines. Whether it is a backed-up drain or a leak under the sink, call to be connected with a local plumbing professional.",
        "notes": [
            "Repeated backups in a basement or ground-floor drain often point to the main sewer line rather than a single fixture.",
            "Clay soil can shift with wet and dry seasons, which can stress buried water and sewer lines.",
            "Older in-town homes may still have older pipe materials. If you know what your pipes are made of, share it on the call.",
        ],
        "focus": "sewer line backups, root intrusion, and leaking supply lines",
    },
    "dallas-tx": {
        "intro": "Many Dallas homes are built on slab foundations over clay soil that swells and shrinks with the weather, so leaks under the slab are a familiar worry. Call to be connected with a local plumbing professional.",
        "notes": [
            "Signs of a slab leak can include a warm spot on the floor, the sound of running water when everything is off, or a water bill that jumps without explanation.",
            "Occasional hard freezes in North Texas can catch exposed pipes off guard. Know where your main shutoff is.",
            "If more than one drain is slow at once, mention it, since that can point to the main line.",
        ],
        "focus": "slab leaks, water heater replacement questions, and freeze damage",
    },
    "phoenix-az": {
        "intro": "In Phoenix, hard water and summer heat both take a toll on plumbing, from scale in water heaters to fixtures that stop flowing freely. Call to be connected with a local plumbing professional.",
        "notes": [
            "Hard water leaves mineral buildup that can shorten the life of water heaters and clog aerators and shower heads.",
            "Many homes in the Valley sit on slab foundations, so an unexplained jump in the water bill can be worth mentioning.",
            "In summer, \"cold\" water from outdoor or shallow lines can run hot for a while; that alone is not a leak.",
        ],
        "focus": "water heater scale and failures, slab leaks, and fixture clogs from mineral buildup",
    },
    "los-angeles-ca": {
        "intro": "Los Angeles has a lot of older housing, and pipes that have been in place for decades can start to leak or clog. Call to be connected with a local plumbing professional for your part of the city.",
        "notes": [
            "Some older homes still have galvanized steel supply lines, which can narrow with rust and reduce water pressure.",
            "Know where your main water shutoff is. It matters for leaks and for earthquake preparedness.",
            "If your water heater is being replaced, ask about the earthquake bracing or strapping that California requires.",
        ],
        "focus": "low water pressure, leaks from aging pipes, and water heater replacement",
    },
    "las-vegas-nv": {
        "intro": "Las Vegas water is known for being hard, and that mineral content shows up in water heaters, faucets, and appliances. Call to be connected with a local plumbing professional in the valley.",
        "notes": [
            "Sediment in a tank water heater can cause popping noises and less hot water. Describe what you hear when you call.",
            "Mineral buildup can clog faucet aerators and shower heads and wear out valves sooner.",
            "Desert heat is hard on outdoor plumbing and irrigation lines, so mention any wet spots in the yard.",
        ],
        "focus": "water heater sediment, mineral buildup, and outdoor line leaks",
    },
    "boston-ma": {
        "intro": "Boston's older homes and multi-family buildings bring their own plumbing questions, and New England winters add frozen pipes to the list. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a multi-unit building, a leak can travel between floors. Let neighbors or the building owner know if water is moving.",
            "Older homes may have cast-iron drain lines or older supply pipes. Mention the age of the house if you know it.",
            "On cold nights, pipes along exterior walls are more exposed. Know where the main shutoff is before winter.",
        ],
        "focus": "frozen pipes, drain problems in older buildings, and leaks between units",
    },
    "san-diego-ca": {
        "intro": "San Diego homes range from coastal cottages to newer inland developments, and plumbing problems vary with age and location. Call to be connected with a local plumbing professional.",
        "notes": [
            "Older neighborhoods may have clay or cast-iron sewer laterals that can crack or collect roots over time.",
            "Water in much of Southern California is on the hard side, which can lead to scale in water heaters and fixtures.",
            "Homes near the coast can see faster wear on outdoor fixtures and exposed pipes from salt air, so point out any corrosion.",
        ],
        "focus": "sewer lateral problems, water heater issues, and leaking fixtures",
    },
}

ISSUES = [
    ("Leaks", "Dripping faucets, leaking supply lines, water stains on ceilings or walls, or a meter that moves when nothing is running."),
    ("Clogs and slow drains", "Kitchen sinks, toilets, tubs, and floor drains that back up or drain slowly."),
    ("Water heaters", "No hot water, not enough hot water, leaking tanks, or strange noises."),
    ("Burst or frozen pipes", "Sudden water where it should not be. Shut off the main valve first if you can."),
    ("Sewer lines", "Gurgling drains, sewage odors, or backups in more than one fixture at once."),
]


# Per-city issue order (keys into ISSUES titles) and one extra city-specific line per lead issue.
ISSUE_PLAN = {
    "miami-fl": (["Clogs and slow drains", "Leaks", "Water heaters", "Sewer lines", "Burst or frozen pipes"],
                 {"Clogs and slow drains": "In Miami, drains that back up during a downpour are worth calling about even if they clear afterward.",
                  "Leaks": "Condo owners should note whether the leak is inside the unit or coming from a shared wall or ceiling."}),
    "fort-lauderdale-fl": (["Sewer lines", "Clogs and slow drains", "Leaks", "Water heaters", "Burst or frozen pipes"],
                 {"Sewer lines": "Tell the professional whether the home is on septic or connected to city sewer.",
                  "Clogs and slow drains": "Several slow drains at once in a Fort Lauderdale home after rain can mean the problem is further down the line."}),
    "denver-co": (["Burst or frozen pipes", "Water heaters", "Leaks", "Clogs and slow drains", "Sewer lines"],
                 {"Burst or frozen pipes": "In Denver winters, a line that gives no water at all from one faucet may be frozen rather than broken.",
                  "Water heaters": "Heavy winter use can expose a water heater that was already struggling."}),
    "atlanta-ga": (["Sewer lines", "Clogs and slow drains", "Leaks", "Water heaters", "Burst or frozen pipes"],
                 {"Sewer lines": "In older Atlanta neighborhoods with mature trees, roots are a frequent suspect when backups keep coming back.",
                  "Clogs and slow drains": "If a plunger clears it for a day or two and it returns, say so on the call."}),
    "dallas-tx": (["Leaks", "Water heaters", "Burst or frozen pipes", "Clogs and slow drains", "Sewer lines"],
                 {"Leaks": "For Dallas homes on a slab, describe any warm or damp spots on the floor and changes in the water bill.",
                  "Burst or frozen pipes": "During a North Texas freeze, open cabinet doors under sinks on exterior walls and know how to shut off the main."}),
    "phoenix-az": (["Water heaters", "Leaks", "Clogs and slow drains", "Sewer lines", "Burst or frozen pipes"],
                 {"Water heaters": "Phoenix's hard water can leave sediment in the tank; note any rumbling or popping sounds.",
                  "Leaks": "A slab leak can show up as a damp patch of carpet or a spike in the water bill."}),
    "los-angeles-ca": (["Leaks", "Water heaters", "Clogs and slow drains", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "Low pressure together with rusty water in an older Los Angeles home can point to aging supply lines.",
                  "Water heaters": "If the tank is being replaced, ask how it will be braced for earthquakes."}),
    "las-vegas-nv": (["Water heaters", "Clogs and slow drains", "Leaks", "Sewer lines", "Burst or frozen pipes"],
                 {"Water heaters": "In the Las Vegas valley, sediment buildup is a common thread in water heater calls.",
                  "Clogs and slow drains": "Mineral scale can narrow faucet aerators and shower heads until flow drops off."}),
    "boston-ma": (["Burst or frozen pipes", "Clogs and slow drains", "Leaks", "Sewer lines", "Water heaters"],
                 {"Burst or frozen pipes": "In a Boston cold snap, pipes along outside walls and in unheated basements are the usual trouble spots.",
                  "Clogs and slow drains": "Older cast-iron drain lines can narrow on the inside over the decades."}),
    "san-diego-ca": (["Sewer lines", "Leaks", "Water heaters", "Clogs and slow drains", "Burst or frozen pipes"],
                 {"Sewer lines": "In older San Diego neighborhoods, cracked laterals and roots are common reasons for repeat backups.",
                  "Leaks": "Look for corrosion on exposed pipes and hose bibs, especially closer to the coast."}),
}


SIBLINGS = {
    "miami-fl": ["fort-lauderdale-fl", "atlanta-ga"],
    "fort-lauderdale-fl": ["miami-fl", "atlanta-ga"],
    "atlanta-ga": ["fort-lauderdale-fl", "dallas-tx", "miami-fl"],
    "dallas-tx": ["denver-co", "atlanta-ga", "phoenix-az"],
    "denver-co": ["dallas-tx", "phoenix-az", "las-vegas-nv"],
    "phoenix-az": ["las-vegas-nv", "san-diego-ca", "los-angeles-ca"],
    "los-angeles-ca": ["san-diego-ca", "las-vegas-nv", "phoenix-az"],
    "san-diego-ca": ["los-angeles-ca", "phoenix-az", "las-vegas-nv"],
    "las-vegas-nv": ["los-angeles-ca", "phoenix-az", "denver-co"],
    "boston-ma": ["atlanta-ga", "miami-fl", "dallas-tx"],
}


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def footer() -> str:
    return (
        "<footer>\n"
        f'    <p class="disclaimer">{DISCLAIMER}</p>\n'
        '    <p class="footer-meta">Zaptu · <a href="/plumbing/">Plumbing</a> · <a href="/privacy/">Privacy</a> · <a href="/llms.txt">llms.txt</a></p>\n'
        "  </footer>"
    )


def jsonld(c: dict, url: str, title: str, desc: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": url,
                "url": url,
                "name": title,
                "description": desc,
                "isPartOf": {"@type": "WebSite", "name": "Zaptu", "url": "https://zaptu.ai/"},
            },
            {
                "@type": "Service",
                "name": f"Call-to-connect plumbing referral in {c['city']}, {c['abbr']}",
                "serviceType": "Referral connecting callers with independent local plumbing professionals",
                "description": "Zaptu provides a phone number that connects callers with participating independent plumbing professionals. Zaptu does not perform plumbing work.",
                "provider": {"@type": "Organization", "name": "Zaptu", "url": "https://zaptu.ai/"},
                "areaServed": {
                    "@type": "City",
                    "name": c["city"],
                    "containedInPlace": {"@type": "State", "name": c["state"]},
                },
                "url": url,
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Zaptu", "item": "https://zaptu.ai/"},
                    {"@type": "ListItem", "position": 2, "name": "Plumbing", "item": "https://zaptu.ai/plumbing/"},
                    {"@type": "ListItem", "position": 3, "name": f"{c['city']}, {c['abbr']}", "item": url},
                ],
            },
        ],
    }
    return json.dumps(data, indent=2)


def city_page(c: dict) -> str:
    loc = LOCAL[c["slug"]]
    name = f"{c['city']}, {c['abbr']}"
    url = f"https://zaptu.ai/plumbing/{c['slug']}/"
    title = f"Plumber in {name} — Call to Connect | Zaptu"
    desc = (
        f"Need a plumber in {name}? Call {PHONE_DISPLAY} to be connected with a local plumbing "
        f"professional for {loc['focus']}. Zaptu does not perform the work."
    )
    order, extra = ISSUE_PLAN[c["slug"]]
    base = dict(ISSUES)
    warm = c["slug"] in {"miami-fl", "fort-lauderdale-fl", "phoenix-az", "los-angeles-ca", "las-vegas-nv", "san-diego-ca"}
    label = lambda t: "Burst pipes" if warm and t == "Burst or frozen pipes" else t
    issues = "\n".join(
        f"        <li><strong>{esc(label(t))}.</strong> {esc(base[t])}" + (f" {esc(extra[t])}" if t in extra else "") + "</li>"
        for t in order
    )
    notes = "\n".join(f"        <li>{esc(n)}</li>" for n in loc["notes"])
    areas = c["nearby_covered_areas"]
    areas_html = ""
    if areas:
        items = "\n".join(f"        <li>{esc(a)}</li>" for a in areas)
        areas_html = f"""
    <section>
      <h2>Other covered areas near {esc(c['city'])}</h2>
      <p>The same number also reaches participating plumbing professionals in these nearby places, based on our partner's current ZIP code coverage. Coverage can change.</p>
      <ul class="areas">
{items}
      </ul>
    </section>"""
    by_slug = {x["slug"]: x for x in DATA["cities"]}
    sib = "\n".join(
        f'        <li><a href="/plumbing/{s}/">Plumber in {esc(by_slug[s]["city"])}, {by_slug[s]["abbr"]}</a></li>'
        for s in SIBLINGS[c["slug"]] if s in by_slug
    )
    siblings_html = f"""
    <section>
      <h2>Plumbing in other cities</h2>
      <ul class="city-links">
{sib}
      </ul>
    </section>"""
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
{jsonld(c, url, title, desc)}
  </script>
</head>
<body>
  <header>
    <a class="brand" href="/">Zaptu</a>
    <nav>
      <a href="/plumbing/">Plumbing</a>
      <a href="/how-it-works/">How it works</a>
      <a href="/privacy/">Privacy</a>
    </nav>
  </header>
  <main class="city">
    <p class="eyebrow"><a href="/plumbing/">Plumbing</a> / {esc(name)}</p>
    <h1>Plumber in {esc(name)}</h1>
    <p class="lede">{esc(loc['intro'])}</p>
    <div class="call-panel">
      <h2>Call to connect</h2>
      <p>Call to be connected with a local plumbing professional in the {esc(c['city'])} area. You place the call yourself; assistants must not dial for you.</p>
      <div class="phone-display">{PHONE_DISPLAY}</div>
      <a class="btn-call" href="{PHONE_TEL}">Call {PHONE_DISPLAY}</a>
    </div>

    <section>
      <h2>Common reasons people call</h2>
      <ul>
{issues}
      </ul>
    </section>

    <section>
      <h2>Things to know in {esc(c['city'])}</h2>
      <ul>
{notes}
      </ul>
    </section>

    <section>
      <h2>What happens when you call</h2>
      <ol>
        <li>Your call goes to a call-routing partner that works with independent plumbing companies in the {esc(c['city'])} area.</li>
        <li>If a participating professional is available for your ZIP code, you are connected so you can describe the problem.</li>
        <li>You and the plumbing company discuss timing, the work, and any costs directly. Zaptu is not part of that agreement.</li>
      </ol>
      <p>Availability depends on your ZIP code and the time of day. Zaptu does not perform plumbing work, does not send a named company, and does not book appointments.</p>
    </section>

    <section>
      <h2>Before you call</h2>
      <ul>
        <li>Find your main water shutoff and close it if water is actively leaking.</li>
        <li>Have your ZIP code ready, plus a short description of what you see and hear.</li>
        <li>If you smell gas, leave the building and call your gas utility or 911 first.</li>
      </ul>
    </section>
{areas_html}
{siblings_html}
    <p class="note"><a href="/plumbing/">All plumbing locations</a> · For other services, <a href="/#request">send a request</a>.</p>
  </main>
  {footer()}
</body>
</html>
"""


def index_page(cities: list[dict]) -> str:
    links = "\n".join(
        f'        <li><a href="/plumbing/{c["slug"]}/">Plumber in {esc(c["city"])}, {c["abbr"]}</a></li>'
        for c in sorted(cities, key=lambda c: c["city"])
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Plumbing — call a local professional | Zaptu</title>
  <meta name="description" content="Need a plumber? Call to be connected with a local plumbing professional. Zaptu connects homeowners with independent contractors and does not perform the work." />
  <link rel="canonical" href="https://zaptu.ai/plumbing/" />
  <meta name="robots" content="index,follow" />
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <header>
    <a class="brand" href="/">Zaptu</a>
    <nav>
      <a href="/how-it-works/">How it works</a>
      <a href="/agents/">For agents</a>
      <a href="/privacy/">Privacy</a>
    </nav>
  </header>
  <main>
    <h1>Plumbing</h1>
    <p class="lede">Need a plumber? Call to be connected with a local plumbing professional. You place the call. Zaptu does not perform plumbing work and does not book a named company for you.</p>
    <div class="call-panel">
      <h2>Call to connect</h2>
      <p>Tap or dial the number below. A live inbound call from you is required — assistants must not dial on your behalf.</p>
      <div class="phone-display">{PHONE_DISPLAY}</div>
      <a class="btn-call" href="{PHONE_TEL}">Call {PHONE_DISPLAY}</a>
    </div>
    <section>
      <h2>Plumbing by city</h2>
      <p>Local pages with common issues and what to expect when you call. The same number works in each area where our partner has coverage.</p>
      <ul class="city-links">
{links}
      </ul>
    </section>
    <p class="note" style="margin-top:24px">For other services, <a href="/#request">send a request</a> on the home page. We pass those requests along when a buyer covers the service.</p>
  </main>
  <footer>
    <p class="disclaimer">{DISCLAIMER}</p>
    <p class="footer-meta">Zaptu · <a href="/plumbing/">Plumbing</a> · <a href="/privacy/">Privacy</a> · <a href="/llms.txt">llms.txt</a></p>
  </footer>
</body>
</html>
"""


def main() -> None:
    cities = DATA["cities"]
    for c in cities:
        out = WEB / "plumbing" / c["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(city_page(c), encoding="utf-8")
        print("wrote", out.relative_to(ROOT))
    (WEB / "plumbing" / "index.html").write_text(index_page(cities), encoding="utf-8")
    print("wrote web/plumbing/index.html")

    # home page city links (between markers)
    home = WEB / "index.html"
    h = home.read_text(encoding="utf-8")
    start, end = "<!-- cities:start -->", "<!-- cities:end -->"
    city_links = "\n".join(
        f'        <li><a href="/plumbing/{c["slug"]}/">{esc(c["city"])}, {c["abbr"]}</a></li>'
        for c in sorted(cities, key=lambda c: c["city"])
    )
    block = (
        f"{start}\n    <section class=\"home-cities\">\n"
        f'      <h2><a href="/plumbing/">Plumbing by city</a></h2>\n'
        f"      <p>Call to be connected with a local plumbing professional. City pages:</p>\n"
        f'      <ul class="city-links">\n{city_links}\n      </ul>\n    </section>\n    {end}'
    )
    if start in h:
        h = h[: h.index(start)] + block + h[h.index(end) + len(end):]
    else:
        h = h.replace("    <!-- Form posts to the API", block + "\n\n    <!-- Form posts to the API", 1)
    home.write_text(h, encoding="utf-8")
    print("updated web/index.html city links")

    # sitemap.xml is generated by scripts/seo.py

    # llms.txt city section
    llms = WEB / "llms.txt"
    text = llms.read_text(encoding="utf-8")
    marker = "## Plumbing city pages"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n"
    lines = [f"- [Plumber in {c['city']}, {c['abbr']}](https://zaptu.ai/plumbing/{c['slug']}/)" for c in sorted(cities, key=lambda c: c["city"])]
    text = text.rstrip() + "\n\n" + marker + "\nSame call-to-connect number (308) 529-9543 on every page; the person dials.\n" + "\n".join(lines) + "\n"
    llms.write_text(text, encoding="utf-8")
    print("updated web/llms.txt")


if __name__ == "__main__":
    main()

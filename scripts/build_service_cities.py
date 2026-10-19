"""Build garage-door, pest-control, HVAC, and handyman hubs, plus city pages where coverage exists.

No buyer phone numbers exist for these categories, so pages use the request form only and must
never show the plumbing tracking number. HVAC and handyman have hubs only: there is no city
coverage data, and none is invented. Copy rules (The Client Connector, applied site-wide):
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
        "covers_note": "These are common garage door problems people describe in a request. Springs and cables are under tension, so leave them alone and write down what the door is doing.",
        "include": [
            "Whether the door is stuck open, stuck closed, or stops partway.",
            "Whether a vehicle is trapped inside the garage.",
            "Any bang, grinding, or a door that reverses on its own.",
            "The age of the door or opener, if known.",
            "Whether the opener has been unplugged.",
        ],
        "faq": [
            ("Does Zaptu do the repair?", "No. Zaptu passes requests to participating independent providers and does not perform the work, send a named company, or set prices."),
            ("Is a callback promised?", "No. A callback depends on whether a participating provider covers the ZIP code on the request."),
            ("Who checks licensing and insurance?", "The homeowner does. License and insurance rules vary by state and by the job. Zaptu does not check them and does not perform the work."),
            ("Should the springs be adjusted before sending a request?", "No. Torsion springs and the cables attached to them hold a lot of tension. Leave them alone, keep people and pets out from under a stuck-open door, and describe what the door is doing in the request."),
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
        "covers_note": "These are common pest problems people describe in a request. Write down what you see, where it is, and when it shows up. Zaptu does not perform pest control.",
        "include": [
            "Which pests, and the rooms or outdoor areas where they show up.",
            "The time of day, and whether it started after rain or a cold snap.",
            "Whether children or pets live in the home.",
            "Any product already put down, and where it is.",
        ],
        "faq": [
            ("Does Zaptu do the repair?", "No. Zaptu passes requests to participating independent providers and does not perform the work, send a named company, or set prices."),
            ("Is a callback promised?", "No. A callback depends on whether a participating provider covers the ZIP code on the request."),
            ("Who checks licensing and insurance?", "The homeowner does. License and insurance rules vary by state and by the job. Zaptu does not check them and does not perform the work."),
            ("What detail helps with a pest request?", "Name the pest if it is known, where it shows up, and when. Mention children or pets in the home, and any product already put down. Keep children and pets away from that product. Zaptu does not perform pest control."),
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
    "hvac": {
        "service_type": "hvac",
        "label": "HVAC repair",
        "h1": "HVAC repair in {name}",
        "title": "HVAC Repair in {name} — Send a Request | Zaptu",
        "desc": "Need HVAC repair in {name}? Send a request to be connected with an independent local HVAC professional. Zaptu does not perform the work.",
        "hub_title": "HVAC Repair — Send a Request | Zaptu",
        "hub_desc": "Send a request to be connected with an independent local HVAC professional. Zaptu does not perform the work and does not book appointments.",
        "hub_lede": "No cooling, no heat, a leak at the indoor unit, or a system that makes a new noise? Send a request to be connected with an independent local HVAC professional. A request is not a booking. Zaptu does not perform HVAC work and does not send a named company.",
        "covers_note": "An HVAC request describes a heating or cooling problem at a home. That can be no cooling, no heat, a thermostat that does not match the system, weak airflow, a water leak at the indoor unit, a frozen coil, a heat pump, a ductless mini-split, ductwork, or a question about an older system. Zaptu records the request and passes it along when a participating independent provider covers the ZIP code. Zaptu does not perform HVAC work, does not send a named company, and does not set a price or choose between repair and replacement.",
        "issues": [
            ("No cooling, or an air conditioner blowing warm air", "The system runs but the air from the vents stays warm, the outdoor unit is quiet, or the home never catches up on a hot day. Note which rooms stay warm and whether the outdoor unit is spinning."),
            ("No heat, or a furnace or heat pump that will not start", "The thermostat is set to heat and the system stays silent, clicks and stops, or blows air that is not warm. Say whether this is a furnace, a heat pump, or a boiler if that is known."),
            ("Thermostat problems", "The display is blank, the setpoint does not match what the system does, or a schedule seems to fight the setting. A blank display can be dead batteries or a tripped breaker, which is worth a look before the request."),
            ("Weak airflow, uneven rooms, or strange noises and smells", "Some rooms are much warmer or cooler than others, airflow at a vent is weak, or the system rattles, squeals, or gives off a dusty or burning smell. Describe the sound or the smell and which rooms are affected."),
            ("Water leaking from the indoor unit, or a frozen coil", "Water on the floor near the air handler, a drain pan that overflows, or ice on the refrigerant line or the indoor coil. Ice often shows up with weak airflow. Switch the system off if water is near electrical parts."),
            ("Heat pumps and ductless mini-splits", "A heat pump that will not switch between heat and cool, a mini-split head that drips, or a room unit that runs but does not change the room temperature. Name how many heads are in the home and which ones are affected."),
            ("Ductwork and vents", "Ducts that have come loose in an attic, a crawl space, or a basement, vents that will not open, or rooms that never get air while other rooms are fine. Say where the ducts run."),
            ("Seasonal maintenance, or a system near the end of its life", "A system that is old, needs a seasonal check, or raises a repair-versus-replacement question. Share the approximate age and what has already failed. Zaptu does not set a price and does not choose repair or replacement."),
        ],
        "safety": [
            "If there is a smell of gas, leave the home right away and call the gas utility or 911 from outside. Do not stay inside to look for the source.",
            "If a carbon monoxide alarm sounds, get everyone out, including pets, and call 911 from outside.",
            "If there is a burning smell, or water near the unit, switch the system off at the thermostat or at the breaker.",
            "A few checks come first: thermostat mode and batteries, the breaker, and whether the filter is packed with dust. Mention what was already checked.",
            "In extreme heat or cold, take care of people who are vulnerable to the temperature before worrying about the equipment.",
        ],
        "include": [
            "Whether the problem is heating, cooling, or both.",
            "The system type if known: central air, furnace, heat pump, ductless mini-split, or boiler.",
            "The approximate age of the equipment.",
            "What it is doing: not turning on, blowing warm air, short cycling, leaking water, or a noise or smell.",
            "Whether anyone in the home is vulnerable to heat or cold.",
        ],
        "faq": [
            ("Does Zaptu do the repair?", "No. Zaptu passes requests to participating independent providers and does not perform the work, send a named company, or set prices."),
            ("Is a callback promised?", "No. A callback depends on whether a participating provider covers the ZIP code on the request."),
            ("Who checks licensing and insurance?", "The homeowner does. License and insurance rules vary by state and by the job. Zaptu does not check them and does not perform the work."),
            ("What should the notes say about the system?", "Say whether the problem is heating, cooling, or both. Add the system type if known, such as central air, a furnace, a heat pump, a ductless mini-split, or a boiler. Add the approximate age and what the system is doing, such as not turning on, blowing warm air, short cycling, leaking water, or making a noise or a smell. Note whether anyone in the home is vulnerable to heat or cold."),
        ],
        "cities": [],
        "local": {},
        "siblings_label": "HVAC repair in",
    },
    "handyman": {
        "service_type": "handyman",
        "label": "Handyman",
        "h1": "Handyman services in {name}",
        "title": "Handyman Services in {name} — Send a Request | Zaptu",
        "desc": "Need a handyman in {name}? Send a request to be connected with an independent local handyman. Zaptu does not perform the work.",
        "hub_title": "Handyman Services — Send a Request | Zaptu",
        "hub_desc": "Send a request to be connected with an independent local handyman. Zaptu does not perform the work and does not book appointments.",
        "hub_lede": "A hole in the drywall, a door that sticks, or a shelf that needs to go up? Send a request to be connected with an independent local handyman. A request is not a booking. Zaptu does not perform the work and does not send a named company.",
        "covers_note": "A handyman request is for smaller jobs around a home: patching drywall, a door that sticks, hinges and knobs, mounting a shelf, a mirror, a curtain rod, or a TV, caulking a tub, a sink, or a window, a short carpentry or trim task, putting furniture or a fixture together, or a small exterior fix such as a fence picket, a gate, or a screen. Zaptu records the request and passes it along when a participating independent provider covers the ZIP code. Zaptu does not perform the work and does not send a named company.",
        "issues": [
            ("Drywall holes and patching", "Nail pops, doorknob holes, and small cracks or holes in walls and ceilings. Describe the room, about how large each hole is, and whether paint is already on hand."),
            ("Doors that stick, plus hinges, knobs and lock hardware", "A door that rubs the frame, a loose hinge, a knob that spins, or lock hardware that no longer lines up. Say whether it is an interior door or an exterior door."),
            ("Mounting shelves, mirrors, curtain rods and TVs", "Items that need to be fastened to a wall, including shelves, mirrors, curtain rods and TVs. Note the wall type if known, such as drywall or plaster, and the approximate size."),
            ("Caulking and sealing around tubs, sinks and windows", "Gaps around a tub, a sink, or a window that let in water or a draft. Say which rooms and whether the old caulk is still in place."),
            ("Minor carpentry and trim", "Loose baseboard, a missing piece of trim, a small shelf, or another short carpentry task. Describe the room and the material."),
            ("Furniture and fixture assembly", "Flat-pack furniture, a fixture that arrived in a box, or hardware that still needs to be put together. Note how many pieces and whether the instructions are on hand."),
            ("Small exterior fixes", "A fence picket, a gate that sags, a torn screen, or another small exterior item. Say whether the work is at ground level and which side of the home it is on."),
        ],
        "safety": [
            "Electrical work, gas work, and plumbing beyond a simple fixture swap may legally require a trade license. The rule depends on the state, the local area, and the size of the job, so the homeowner should confirm before anyone starts.",
            "Do not open walls where wiring or pipes might run.",
            "Shut off water or power before anyone works near them.",
        ],
        "include": [
            "The rooms or areas where the work is.",
            "A plain description of each item, specific enough that a photo would match it.",
            "A rough size for each item, such as the width of a hole or the length of a shelf.",
            "Whether materials, such as paint, caulk, or hardware, are already on hand.",
        ],
        "faq": [
            ("Does Zaptu do the repair?", "No. Zaptu passes requests to participating independent providers and does not perform the work, send a named company, or set prices."),
            ("Is a callback promised?", "No. A callback depends on whether a participating provider covers the ZIP code on the request."),
            ("Who checks licensing and insurance?", "The homeowner does. License and insurance rules vary by state and by the job. Zaptu does not check them and does not perform the work."),
            ("What kinds of jobs fit a handyman request?", "Smaller jobs around the home fit this request: drywall holes and patching, doors that stick, hinges, knobs and lock hardware, mounting shelves, mirrors, curtain rods and TVs, caulking and sealing around tubs, sinks and windows, minor carpentry and trim, furniture and fixture assembly, and small exterior fixes such as fences, gates and screens. Electrical work, gas work, and plumbing beyond a simple fixture swap may fall under state and local rules that call for a trade license, depending on the state and the size of the job. The homeowner should confirm that. Zaptu does not perform the work and does not decide which rules apply."),
        ],
        "cities": [],
        "local": {},
        "siblings_label": "Handyman in",
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
      <label class="consent" for="consent_to_contact"><input type="checkbox" id="consent_to_contact" name="consent_to_contact" value="yes" required /><span>I agree Zaptu may share my details with Polyares and its service-provider partners, and that Polyares, those partners, or Zaptu may call or text about this request.</span></label>
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
    data.consent_source_page = location.pathname;
    if (q.get("dry_run") === "1") data.dry_run = true;
    if (!data.dry_run) {  // backup copy to Netlify Forms (emails a notification); never blocks the intake post
      try {
        var nb = new URLSearchParams();
        new FormData(f).forEach(function (v, k) { nb.append(k, v); });
        nb.set("form-name", "service-request");
        nb.set("consent_source_page", location.pathname);
        if (!nb.has("bot-field")) nb.set("bot-field", "");
        fetch("/", { method: "POST", keepalive: true, headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: nb.toString() }).catch(function () {});
      } catch (err) {}
    }
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


def bullets(items: list) -> str:
    lines = []
    for item in items:
        if isinstance(item, tuple):
            title, desc = item
            lines.append(f"        <li><strong>{esc(title)}.</strong> {esc(desc)}</li>")
        else:
            lines.append(f"        <li>{esc(item)}</li>")
    return "\n".join(lines)


def after_request_section() -> str:
    return """    <section>
      <h2>What happens after you send a request</h2>
      <ol>
        <li>Zaptu records your request and passes it along when a participating independent provider covers your ZIP code.</li>
        <li>If a provider takes the request, they contact you by phone or text to talk through the problem.</li>
        <li>You and the provider agree on timing, the work, and any costs directly. Zaptu is not part of that agreement.</li>
      </ol>
      <p>A request is not a booking, and a callback is not promised. Zaptu does not perform the work and does not send a named company.</p>
    </section>"""


def faq_block(faq: list[tuple[str, str]]) -> tuple[str, dict]:
    items = "\n".join(f"        <dt>{esc(q)}</dt>\n        <dd>{esc(a)}</dd>" for q, a in faq)
    html_block = f"""    <section>
      <h2>Common questions</h2>
      <dl>
{items}
      </dl>
    </section>"""
    ld = {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    }
    return html_block, ld


def other_hubs_section(cat: str) -> str:
    links = [("plumbing", "Plumbing")] + [(key, svc["label"]) for key, svc in SERVICES.items()]
    items = [f'        <li><a href="/{key}/">{esc(label)}</a></li>' for key, label in links if key != cat]
    items.append('        <li><a href="/how-it-works/">How it works</a></li>')
    body = "\n".join(items)
    return f"""    <section>
      <h2>Other home services</h2>
      <ul class="city-links">
{body}
      </ul>
    </section>"""


def city_page(cat: str, s: dict, slug: str) -> str:
    city, abbr, state = CITIES[slug]
    name = f"{city}, {abbr}"
    url = f"{BASE}/{cat}/{slug}/"
    title, desc = s["title"].format(name=name), s["desc"].format(name=name)
    intro, notes = s["local"][slug]
    issues = bullets(s["issues"])
    notes_html = bullets(notes)
    safety = bullets(s["safety"])
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

{after_request_section()}

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
    faq_html, faq_ld = faq_block(s["faq"])
    city_section = ""
    if s["cities"]:
        links = "\n".join(
            f'        <li><a href="/{cat}/{o}/">{s["siblings_label"]} {esc(CITIES[o][0])}, {CITIES[o][1]}</a></li>'
            for o in sorted(s["cities"], key=lambda o: CITIES[o][0]))
        city_section = f"""
    <section>
      <h2>{s['label']} by city</h2>
      <ul class="city-links">
{links}
      </ul>
    </section>"""
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url, "url": url, "name": s["hub_title"], "description": s["hub_desc"],
         "isPartOf": {"@type": "WebSite", "name": "Zaptu", "url": f"{BASE}/"}},
        faq_ld,
        crumbs([("Zaptu", f"{BASE}/"), (s["label"], url)])]}
    body = f"""  <main class="service-hub">
    <h1>{esc(s['label'])}</h1>
    <p class="lede">{esc(s['hub_lede'])}</p>
{form_html(s['service_type'], s['label'], None, None)}
    <section>
      <h2>What this covers</h2>
      <p>{esc(s['covers_note'])}</p>
      <ul>
{bullets(s['issues'])}
      </ul>
    </section>
    <section>
      <h2>What to include in your request</h2>
      <p>Add the details below in the notes field. A participating provider can use them to understand the request. They do not set an appointment, and Zaptu does not perform the work.</p>
      <ul>
{bullets(s['include'])}
      </ul>
    </section>
{after_request_section()}
    <section>
      <h2>Before someone follows up</h2>
      <ul>
{bullets(s['safety'])}
      </ul>
    </section>
{faq_html}
{other_hubs_section(cat)}{city_section}
  </main>"""
    return page(s["hub_title"], s["hub_desc"], url, body, ld)


def main() -> None:
    llms_lines = []
    for cat, s in SERVICES.items():
        (WEB / cat).mkdir(exist_ok=True)
        (WEB / cat / "index.html").write_text(hub_page(cat, s), encoding="utf-8")
        if s["cities"]:
            llms_lines.append(
                f"\n## {s['label']} city pages\nRequest form only (service_type {s['service_type']}, collecting); no phone number."
            )
        else:
            llms_lines.append(
                f"\n## {s['label']}\nRequest form only (service_type {s['service_type']}, collecting); no phone number. No city pages."
            )
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

"""Build /plumbing/<slug>/ city pages from scripts/plumbing_cities.json.

Copy rules (The Client Connector): no "free" outside the approved disclaimer, no prices,
no superlatives, no reviews, no licensed/insured/guaranteed/response-time claims, never
imply Zaptu does the work or that a named company is coming.
"""

from __future__ import annotations

import html
import json
import re
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


# Batch 2 (2026-10-12)
LOCAL2 = {
    "boulder-co": {
        "intro": "Boulder sits right against the foothills, and its cold nights and big temperature swings are hard on pipes in exterior walls, crawl spaces, and garages. Call to be connected with a local plumbing professional.",
        "notes": [
            "Before a hard freeze, disconnect garden hoses and know where your main shutoff valve is.",
            "Homes in the foothills and canyons may use a well or septic system. Say which you have when you call.",
            "Older homes near downtown and the university can have older supply and drain lines, so mention the age of the house if you know it.",
        ],
        "focus": "frozen or burst pipes, water heater outages, and leaks in older homes",
    },
    "fort-collins-co": {
        "intro": "Fort Collins winters bring regular freezes, and pipes in crawl spaces, garages, and outside walls feel it first. Call to be connected with a local plumbing professional.",
        "notes": [
            "Turn off and drain sprinkler lines and outdoor spigots before the first hard freeze.",
            "A frozen pipe can start leaking hours after it thaws, so keep an eye on nearby walls and ceilings.",
            "Homes outside town may be on a well or septic system. Mention it on the call.",
        ],
        "focus": "frozen pipes, sprinkler and outdoor line problems, and water heater issues",
    },
    "fort-worth-tx": {
        "intro": "Many Fort Worth homes sit on slab foundations over clay soil that swells and shrinks with the weather, so leaks under the slab are a common concern. Call to be connected with a local plumbing professional.",
        "notes": [
            "A warm spot on the floor, running-water sounds when everything is off, or a water bill that jumps can point to a slab leak.",
            "Hard freezes in North Texas are not frequent, but they can catch exposed pipes unprepared. Know where your main shutoff is.",
            "If several drains slow down at once, say so, since that can point to the main sewer line.",
        ],
        "focus": "slab leaks, freeze damage, and main line backups",
    },
    "west-palm-beach-fl": {
        "intro": "West Palm Beach has older bungalows, newer subdivisions, and waterfront condos, and plumbing questions differ for each. Call to be connected with a local plumbing professional.",
        "notes": [
            "Some properties in Palm Beach County use septic systems. Say whether you are on septic or city sewer.",
            "Heavy summer rain can push water back up through floor drains. Stop running water until the line is checked.",
            "Salt air can wear on outdoor fixtures and exposed pipes, so mention any corrosion you see.",
        ],
        "focus": "drain backups after storms, septic and sewer questions, and leaking fixtures",
    },
    "sacramento-ca": {
        "intro": "Sacramento has many older neighborhoods with mature trees, and both age and roots can affect supply and sewer lines. Call to be connected with a local plumbing professional.",
        "notes": [
            "Repeated backups in the same drain often point to roots or a problem in the sewer lateral.",
            "Hot summers are hard on outdoor plumbing and irrigation lines. Mention any wet patches in the yard.",
            "If your water heater is being replaced, ask about the earthquake strapping that California requires.",
        ],
        "focus": "sewer lateral and root problems, leaks from aging pipes, and water heater replacement",
    },
    "san-antonio-tx": {
        "intro": "San Antonio's water is on the hard side, and many homes sit on slabs over shifting soil, so scale and under-slab leaks come up often. Call to be connected with a local plumbing professional.",
        "notes": [
            "Mineral buildup can shorten the life of water heaters and clog aerators and shower heads.",
            "An unexplained rise in the water bill or a damp spot on the floor can be worth mentioning for a home on a slab.",
            "Occasional hard freezes can affect exposed pipes. Know where your main shutoff valve is.",
        ],
        "focus": "water heater scale, slab leaks, and freeze damage",
    },
    "kansas-city-mo": {
        "intro": "Kansas City sees cold winters and stormy springs, so frozen pipes and wet basements are both familiar problems. Call to be connected with a local plumbing professional.",
        "notes": [
            "If your home has a sump pump, check that it runs before the spring storm season.",
            "Pipes along exterior walls and in unheated basements are more likely to freeze on cold nights.",
            "Older homes may have cast-iron or clay drain lines. Mention the age of the house if you know it.",
        ],
        "focus": "frozen pipes, basement drain and sump problems, and sewer line backups",
    },
    "oklahoma-city-ok": {
        "intro": "Oklahoma City weather swings from summer heat to winter ice, and clay soil moves with it, which can stress pipes in and under the house. Call to be connected with a local plumbing professional.",
        "notes": [
            "Shifting soil can stress slab foundations and buried lines, so mention any new cracks or damp spots.",
            "During ice storms, open cabinet doors under sinks on outside walls and know where the main shutoff is.",
            "Repeated backups in more than one drain can point to the main sewer line.",
        ],
        "focus": "slab and buried line leaks, freeze damage, and sewer backups",
    },
    "san-francisco-ca": {
        "intro": "San Francisco has a large share of older buildings, including Victorians and multi-unit flats, and pipes that have been in place for decades can leak or clog. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a multi-unit building, a leak can travel between floors. Let neighbors or the building owner know if water is moving.",
            "Older buildings may have galvanized supply lines or cast-iron drains. Mention the age of the building if you know it.",
            "If your water heater is being replaced, ask about the earthquake strapping that California requires.",
        ],
        "focus": "leaks in older buildings, drain problems, and water heater replacement",
    },
    "boca-raton-fl": {
        "intro": "Boca Raton has many condos and planned communities alongside single-family homes, and who handles a plumbing problem can depend on where it starts. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a condo or HOA community, check whether the association needs to know before work starts.",
            "Heavy rain can overwhelm drains. If water comes up through a floor drain or shower, stop running water until it is checked.",
            "Humid, salty air can wear on outdoor fixtures and exposed pipes, so mention any corrosion.",
        ],
        "focus": "condo leaks, drain backups after storms, and water heater problems",
    },
}
PLAN2 = {
    "boulder-co": (["Burst or frozen pipes", "Water heaters", "Leaks", "Clogs and slow drains", "Sewer lines"],
                 {"Burst or frozen pipes": "In a Boulder cold snap, a faucet that gives no water at all may be frozen rather than broken.",
                  "Water heaters": "Heavy winter use can expose a water heater that was already struggling."}),
    "fort-collins-co": (["Burst or frozen pipes", "Leaks", "Water heaters", "Clogs and slow drains", "Sewer lines"],
                 {"Burst or frozen pipes": "In Fort Collins, sprinkler lines and outdoor spigots left charged are frequent freeze trouble spots.",
                  "Leaks": "Check crawl spaces and garages after a thaw for water that was not there before."}),
    "fort-worth-tx": (["Leaks", "Sewer lines", "Burst or frozen pipes", "Water heaters", "Clogs and slow drains"],
                 {"Leaks": "For Fort Worth homes on a slab, describe any warm or damp spots on the floor and changes in the water bill.",
                  "Sewer lines": "Soil movement can stress buried sewer lines, so mention repeat backups."}),
    "west-palm-beach-fl": (["Clogs and slow drains", "Sewer lines", "Leaks", "Water heaters", "Burst or frozen pipes"],
                 {"Clogs and slow drains": "In West Palm Beach, drains that back up during a downpour are worth calling about even if they clear afterward.",
                  "Sewer lines": "Tell the professional whether the home is on septic or connected to city sewer."}),
    "sacramento-ca": (["Sewer lines", "Leaks", "Water heaters", "Clogs and slow drains", "Burst or frozen pipes"],
                 {"Sewer lines": "In older Sacramento neighborhoods with large trees, roots are a frequent suspect when backups keep returning.",
                  "Leaks": "Low pressure together with rusty water in an older home can point to aging supply lines."}),
    "san-antonio-tx": (["Water heaters", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Sewer lines"],
                 {"Water heaters": "San Antonio's hard water can leave sediment in the tank; note any rumbling or popping sounds.",
                  "Leaks": "A slab leak can show up as a damp patch of flooring or a spike in the water bill."}),
    "kansas-city-mo": (["Burst or frozen pipes", "Sewer lines", "Clogs and slow drains", "Leaks", "Water heaters"],
                 {"Burst or frozen pipes": "In a Kansas City cold snap, pipes along outside walls and in unheated basements are the usual trouble spots.",
                  "Sewer lines": "Water coming up through a basement floor drain during heavy rain can point to the sewer line."}),
    "oklahoma-city-ok": (["Leaks", "Burst or frozen pipes", "Sewer lines", "Water heaters", "Clogs and slow drains"],
                 {"Leaks": "For Oklahoma City homes on a slab, describe damp spots, warm floors, or a jump in the water bill.",
                  "Burst or frozen pipes": "During an ice storm, let faucets on outside walls drip and know how to shut off the main."}),
    "san-francisco-ca": (["Leaks", "Clogs and slow drains", "Water heaters", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "In San Francisco flats, note whether the leak is inside your unit or coming from above.",
                  "Clogs and slow drains": "Older cast-iron drain lines can narrow on the inside over the decades."}),
    "boca-raton-fl": (["Leaks", "Clogs and slow drains", "Water heaters", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "Condo owners in Boca Raton should note whether the leak is inside the unit or coming from a shared wall or ceiling.",
                  "Clogs and slow drains": "Drains that back up during a downpour are worth calling about even if they clear afterward."}),
}
SIB2 = {
    "boulder-co": ["denver-co", "fort-collins-co", "phoenix-az"],
    "fort-collins-co": ["boulder-co", "denver-co", "kansas-city-mo"],
    "fort-worth-tx": ["dallas-tx", "oklahoma-city-ok", "san-antonio-tx"],
    "west-palm-beach-fl": ["boca-raton-fl", "fort-lauderdale-fl", "miami-fl"],
    "sacramento-ca": ["san-francisco-ca", "los-angeles-ca", "las-vegas-nv"],
    "san-antonio-tx": ["fort-worth-tx", "dallas-tx", "oklahoma-city-ok"],
    "kansas-city-mo": ["oklahoma-city-ok", "denver-co", "dallas-tx"],
    "oklahoma-city-ok": ["fort-worth-tx", "kansas-city-mo", "dallas-tx"],
    "san-francisco-ca": ["sacramento-ca", "los-angeles-ca", "san-diego-ca"],
    "boca-raton-fl": ["west-palm-beach-fl", "fort-lauderdale-fl", "miami-fl"],
}

LOCAL.update(LOCAL2)
ISSUE_PLAN.update(PLAN2)
SIBLINGS.update(SIB2)
# Batch 1 pages also link to batch 2 neighbours.
for _k, _v in {"denver-co": "boulder-co", "dallas-tx": "fort-worth-tx", "fort-lauderdale-fl": "west-palm-beach-fl", "miami-fl": "boca-raton-fl", "los-angeles-ca": "san-francisco-ca", "san-diego-ca": "san-francisco-ca", "atlanta-ga": "kansas-city-mo"}.items():
    if _v not in SIBLINGS[_k]:
        SIBLINGS[_k].append(_v)


# Batch 3 (2026-10-13)
LOCAL3 = {
    "memphis-tn": {
        "intro": "Memphis has many older homes with mature trees, along with humid summers, heavy spring rain, and the occasional winter ice storm, all of which can affect pipes and drains. Call to be connected with a local plumbing professional.",
        "notes": [
            "Tree roots can work their way into older sewer lines, so repeat backups in the same drain are worth mentioning.",
            "During an ice storm or hard freeze, open cabinet doors under sinks on outside walls and know where your main shutoff valve is.",
            "Older homes in established neighborhoods may have older pipe materials. Mention the age of the house if you know it.",
        ],
        "focus": "sewer backups and root problems, freeze damage, and leaking fixtures",
    },
    "portland-or": {
        "intro": "Portland's long, wet season puts a steady load on drains, sewer lines, and basements, and older homes with mature trees add their own plumbing questions. Call to be connected with a local plumbing professional.",
        "notes": [
            "Water in a basement during the rainy months can come from a drain or sewer line, not only from outside. Describe where it appears.",
            "Roots from large street and yard trees can get into older sewer lines and cause repeat backups.",
            "Cold snaps and ice storms do happen. Disconnect garden hoses and know where your main shutoff valve is before winter.",
        ],
        "focus": "basement drain and sewer problems, root intrusion, and leaks in older homes",
    },
    "salt-lake-city-ut": {
        "intro": "Salt Lake City winters bring regular freezes, and the water in much of the valley is on the hard side, so frozen lines and water heater scale both come up. Call to be connected with a local plumbing professional.",
        "notes": [
            "Before the first hard freeze, drain sprinkler lines and outdoor spigots and disconnect garden hoses.",
            "Hard water can leave mineral buildup in water heaters and clog faucet aerators and shower heads.",
            "Many homes have basements. If water shows up near a floor drain or the water heater, mention where it is coming from.",
        ],
        "focus": "frozen pipes, water heater scale and failures, and basement leaks",
    },
    "baltimore-md": {
        "intro": "Baltimore has a large stock of older rowhomes, and shared walls, old drain lines, and cold winters shape a lot of plumbing problems. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a rowhome, a leak can reach the house next door. Let your neighbor know if water may be crossing a shared wall.",
            "Older homes may have cast-iron or clay drain lines and older supply pipes. Mention the age of the house if you know it.",
            "On cold nights, pipes along exterior walls and in unheated basements are more exposed. Know where the main shutoff is.",
        ],
        "focus": "drain and sewer problems in older homes, frozen pipes, and leaks between rowhomes",
    },
}
PLAN3 = {
    "memphis-tn": (["Sewer lines", "Clogs and slow drains", "Leaks", "Burst or frozen pipes", "Water heaters"],
                 {"Sewer lines": "In older Memphis neighborhoods with large trees, roots are a frequent suspect when backups keep returning.",
                  "Clogs and slow drains": "If more than one drain slows down after heavy rain, say so on the call."}),
    "portland-or": (["Sewer lines", "Clogs and slow drains", "Leaks", "Water heaters", "Burst or frozen pipes"],
                 {"Sewer lines": "In Portland's rainy months, water coming up through a basement floor drain can point to the sewer line.",
                  "Clogs and slow drains": "If a plunger clears it for a day or two and it returns, mention that."}),
    "salt-lake-city-ut": (["Burst or frozen pipes", "Water heaters", "Leaks", "Clogs and slow drains", "Sewer lines"],
                 {"Burst or frozen pipes": "In a Salt Lake City cold snap, sprinkler lines and outdoor spigots left charged are frequent trouble spots.",
                  "Water heaters": "Hard water can leave sediment in the tank; note any rumbling or popping sounds."}),
    "baltimore-md": (["Clogs and slow drains", "Burst or frozen pipes", "Leaks", "Sewer lines", "Water heaters"],
                 {"Clogs and slow drains": "Older cast-iron drain lines in Baltimore rowhomes can narrow on the inside over the decades.",
                  "Burst or frozen pipes": "During a cold snap, pipes in unheated basements and along outside walls are the usual trouble spots."}),
}
SIB3 = {
    "memphis-tn": ["kansas-city-mo", "oklahoma-city-ok", "atlanta-ga"],
    "portland-or": ["sacramento-ca", "san-francisco-ca", "salt-lake-city-ut"],
    "salt-lake-city-ut": ["denver-co", "phoenix-az", "las-vegas-nv"],
    "baltimore-md": ["boston-ma", "atlanta-ga", "memphis-tn"],
}

LOCAL.update(LOCAL3)
ISSUE_PLAN.update(PLAN3)
SIBLINGS.update(SIB3)
# Earlier pages also link to batch 3 neighbours.
for _k, _v in [("kansas-city-mo", "memphis-tn"), ("oklahoma-city-ok", "memphis-tn"), ("atlanta-ga", "memphis-tn"),
               ("sacramento-ca", "portland-or"), ("san-francisco-ca", "portland-or"),
               ("denver-co", "salt-lake-city-ut"), ("las-vegas-nv", "salt-lake-city-ut"), ("boston-ma", "baltimore-md")]:
    if _v not in SIBLINGS[_k]:
        SIBLINGS[_k].append(_v)


# Batch 4 (2026-10-15)
LOCAL4 = {
    "marietta-ga": {
        "intro": "Marietta sits northwest of Atlanta, with older in-town houses and newer subdivisions built over Georgia clay and under a heavy tree canopy. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay soil swells when it is wet and shrinks when it dries, which can stress buried water and sewer lines.",
            "Mature trees in established neighborhoods can send roots into older sewer lines. Mention backups that keep returning.",
            "Hard freezes are not a regular event here, but they do happen. Know where your main shutoff valve is.",
        ],
        "focus": "sewer backups from roots, clay-soil line stress, and leaks under slabs or in crawl spaces",
    },
    "arlington-tx": {
        "intro": "Arlington sits between Dallas and Fort Worth, and many homes are built on slab foundations over clay soil that moves with the weather. Call to be connected with a local plumbing professional.",
        "notes": [
            "A warm spot on the floor, running-water sounds when fixtures are off, or a water bill that jumps can point to a leak under the slab.",
            "Hard freezes in North Texas are infrequent, but they can split exposed pipes. Know where the main shutoff is.",
            "If several drains slow down at the same time, say so, since that can point to the main sewer line.",
        ],
        "focus": "slab leaks, exposed-pipe freeze damage, and main sewer line backups",
    },
    "dayton-oh": {
        "intro": "Dayton winters bring regular freezes, and many homes have basements where supply lines, drains, and water heaters sit. Call to be connected with a local plumbing professional.",
        "notes": [
            "Pipes along exterior walls and in unheated spaces are more exposed on cold nights. Know where the main shutoff is.",
            "Older neighborhoods may still have cast-iron or clay drain lines. Mention the age of the house if you know it.",
            "Spring rain can send water toward basement floor drains. Describe where any water appears.",
        ],
        "focus": "frozen pipes, basement drain backups, and leaks in older homes",
    },
    "columbus-oh": {
        "intro": "Columbus mixes older neighborhoods with newer suburbs, and cold winters plus clay soil both show up in plumbing calls. Call to be connected with a local plumbing professional.",
        "notes": [
            "During a hard freeze, open cabinet doors under sinks on outside walls and know how to shut off the main.",
            "Clay around central Ohio can shift between wet and dry spells, which can stress buried lines.",
            "If the house has a sump pump, check that it runs before heavy spring rain.",
        ],
        "focus": "frozen supply lines, sump and sewer trouble, and water heater outages",
    },
    "raleigh-nc": {
        "intro": "Raleigh's red clay, humid summers, and a canopy of pines and hardwoods shape plumbing problems in both older neighborhoods and newer subdivisions. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay soil swells in wet weather and shrinks when it dries, which can stress buried water and sewer lines.",
            "Tree roots can enter older sewer laterals. Describe backups that return after they seem to clear.",
            "Winters are usually mild, but a hard freeze can still catch outdoor spigots. Disconnect garden hoses beforehand.",
        ],
        "focus": "sewer laterals and root intrusion, buried-line stress, and outdoor spigot freezes",
    },
    "boise-id": {
        "intro": "Boise winters bring regular freezes, and sprinkler lines and outdoor spigots need to be drained before the first one. Call to be connected with a local plumbing professional.",
        "notes": [
            "Drain sprinkler lines and outdoor spigots, and disconnect garden hoses, before temperatures stay below freezing.",
            "A pipe that froze can start leaking after it thaws. Check crawl spaces, garages, and exterior walls once it warms.",
            "Homes toward the foothills may be on a well. Say so when you call.",
        ],
        "focus": "frozen pipes, sprinkler and outdoor line damage, and crawl-space leaks",
    },
    "columbia-sc": {
        "intro": "Columbia has hot, humid summers, red clay soil, and mature trees, with an ice storm some winters. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay that swells and shrinks can stress pipes under a slab and in the yard. Mention new damp spots or a jump in the water bill.",
            "Roots from yard and street trees can get into older sewer lines and cause backups that return.",
            "When an ice storm is forecast, know where the main shutoff is and open cabinet doors under sinks on outside walls.",
        ],
        "focus": "clay-soil pipe stress, root-related sewer backups, and ice-storm freeze damage",
    },
    "knoxville-tn": {
        "intro": "Knoxville sits in a valley against the foothills, with older houses, winter cold snaps, and trees that can reach sewer lines. Call to be connected with a local plumbing professional.",
        "notes": [
            "Cold snaps can freeze pipes in crawl spaces, garages, and exterior walls. Know where your main shutoff valve is.",
            "Older neighborhoods often have longer sewer laterals. Repeat backups can point to roots or a break in that line.",
            "Say whether the home has a crawl space, a basement, or a slab, since a leak shows up differently in each.",
        ],
        "focus": "crawl-space freezes, sewer lateral backups, and leaks in older valley homes",
    },
}
PLAN4 = {
    "marietta-ga": (["Sewer lines", "Clogs and slow drains", "Leaks", "Water heaters", "Burst or frozen pipes"],
                 {"Sewer lines": "In Marietta neighborhoods with large trees, roots are a frequent suspect when backups keep returning.",
                  "Leaks": "Clay soil that shifts between wet and dry spells can stress buried supply lines."}),
    "arlington-tx": (["Leaks", "Sewer lines", "Burst or frozen pipes", "Water heaters", "Clogs and slow drains"],
                 {"Leaks": "For Arlington homes on a slab, describe warm or damp spots on the floor and changes in the water bill.",
                  "Burst or frozen pipes": "During a North Texas freeze, open cabinet doors under sinks on exterior walls and know how to shut off the main."}),
    "dayton-oh": (["Burst or frozen pipes", "Clogs and slow drains", "Sewer lines", "Leaks", "Water heaters"],
                 {"Burst or frozen pipes": "In a Dayton cold snap, pipes in unheated basements and along outside walls are the usual trouble spots.",
                  "Clogs and slow drains": "Water coming up through a basement floor drain during spring rain is worth describing on the call."}),
    "columbus-oh": (["Burst or frozen pipes", "Water heaters", "Sewer lines", "Leaks", "Clogs and slow drains"],
                 {"Burst or frozen pipes": "In Columbus, let faucets on outside walls drip during a hard freeze and know where the main shutoff is.",
                  "Water heaters": "No hot water after a cold night can mean the tank, the supply line, or both. Say what you are seeing."}),
    "raleigh-nc": (["Sewer lines", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Water heaters"],
                 {"Sewer lines": "In older Raleigh neighborhoods, roots in the sewer lateral are a frequent reason backups return.",
                  "Burst or frozen pipes": "A hard freeze can split an outdoor spigot or an exposed line even when indoor pipes are fine."}),
    "boise-id": (["Burst or frozen pipes", "Leaks", "Water heaters", "Clogs and slow drains", "Sewer lines"],
                 {"Burst or frozen pipes": "In Boise, sprinkler lines and outdoor spigots left charged are frequent freeze trouble spots.",
                  "Leaks": "After a thaw, look in the crawl space and along exterior walls for water that was not there before."}),
    "columbia-sc": (["Leaks", "Sewer lines", "Clogs and slow drains", "Burst or frozen pipes", "Water heaters"],
                 {"Leaks": "For Columbia homes on a slab over clay, mention damp flooring or a water bill that jumped.",
                  "Sewer lines": "Roots from mature trees are a frequent suspect when the same drain backs up again."}),
    "knoxville-tn": (["Burst or frozen pipes", "Sewer lines", "Leaks", "Clogs and slow drains", "Water heaters"],
                 {"Burst or frozen pipes": "In a Knoxville cold snap, crawl spaces and pipes on outside walls are the usual trouble spots.",
                  "Sewer lines": "A long sewer lateral on a sloped lot can hide a root intrusion or a break. Mention repeat backups."}),
}
SIB4 = {
    "marietta-ga": ["atlanta-ga", "knoxville-tn", "columbia-sc"],
    "arlington-tx": ["dallas-tx", "fort-worth-tx", "oklahoma-city-ok"],
    "dayton-oh": ["columbus-oh", "kansas-city-mo", "baltimore-md"],
    "columbus-oh": ["dayton-oh", "baltimore-md", "kansas-city-mo"],
    "raleigh-nc": ["columbia-sc", "atlanta-ga", "knoxville-tn"],
    "boise-id": ["salt-lake-city-ut", "denver-co", "portland-or"],
    "columbia-sc": ["atlanta-ga", "raleigh-nc", "knoxville-tn"],
    "knoxville-tn": ["atlanta-ga", "memphis-tn", "columbia-sc"],
}

LOCAL.update(LOCAL4)
ISSUE_PLAN.update(PLAN4)
SIBLINGS.update(SIB4)
# Earlier pages also link to batch 4 neighbours.
for _k, _v in [("atlanta-ga", "marietta-ga"), ("dallas-tx", "arlington-tx"), ("fort-worth-tx", "arlington-tx"),
               ("kansas-city-mo", "dayton-oh"), ("baltimore-md", "columbus-oh"),
               ("memphis-tn", "knoxville-tn"), ("salt-lake-city-ut", "boise-id"),
               ("portland-or", "boise-id"), ("denver-co", "boise-id")]:
    if _v not in SIBLINGS[_k]:
        SIBLINGS[_k].append(_v)


# Batch 5 (2026-10-15)
LOCAL5 = {
    "arlington-va": {
        "intro": "Arlington mixes older garden apartments, mid-rise buildings, and houses between the Potomac and Fairfax County. A leak in a stacked unit travels differently from one in a single-family home. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a multi-unit building, water can reach the unit below. Check whether building management needs to know before work starts.",
            "Older buildings may still have galvanized supply lines or cast-iron drains. Mention the age of the building if you know it.",
            "Winter cold snaps can freeze pipes in exterior walls and unheated spaces. Know where the main shutoff is.",
        ],
        "focus": "leaks between units, drain problems in older buildings, and freeze damage",
    },
    "greensboro-nc": {
        "intro": "Greensboro sits in the Piedmont, with red clay soil, humid summers, and a mix of older neighborhoods and newer subdivisions. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay soil swells when it is wet and shrinks when it dries, which can stress buried water and sewer lines.",
            "Mature trees can send roots into older sewer laterals. Mention backups that keep returning.",
            "Winters are usually mild, but a hard freeze can still split an outdoor spigot. Disconnect garden hoses beforehand.",
        ],
        "focus": "sewer laterals and root intrusion, buried-line stress from clay, and outdoor spigot freezes",
    },
    "winston-salem-nc": {
        "intro": "Winston Salem spreads across Piedmont hills, with older in-town houses, mill neighborhoods, and newer subdivisions on clay soil. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay that shifts between wet and dry spells can stress pipes under a slab and in the yard.",
            "Roots from yard and street trees can get into older sewer lines and cause backups that return.",
            "On a cold night, pipes in crawl spaces and along outside walls are more exposed. Know where the main shutoff is.",
        ],
        "focus": "clay-soil pipe stress, root-related sewer backups, and crawl-space leaks",
    },
    "harrisburg-pa": {
        "intro": "Harrisburg winters bring regular freezes, and many homes have basements where supply lines, drains, and water heaters sit. The river valley also sees heavy spring rain. Call to be connected with a local plumbing professional.",
        "notes": [
            "Pipes along exterior walls and in unheated basements are more exposed on cold nights. Know where the main shutoff is.",
            "Older neighborhoods may still have cast-iron or clay drain lines. Mention the age of the house if you know it.",
            "Spring rain can send water toward basement floor drains. Describe where any water appears.",
        ],
        "focus": "winter pipe freezes, basement drain backups after spring rain, and water heater outages",
    },
    "new-haven-ct": {
        "intro": "New Haven mixes older homes and multi-family buildings with cold, wet winters that are hard on pipes and drains. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a multi-unit house, a leak can travel between floors. Let neighbors or the owner know if water is moving.",
            "Older homes may have cast-iron drain lines or older supply pipes. Mention the age of the house if you know it.",
            "On cold nights, pipes along exterior walls and in unheated basements are more exposed. Know where the main shutoff is.",
        ],
        "focus": "frozen pipes in older houses, drain problems in multi-family buildings, and leaks between floors",
    },
    "fresno-ca": {
        "intro": "Fresno sits in the San Joaquin Valley, where hot, dry summers and hard water take a toll on water heaters and fixtures, and winter nights can still freeze outdoor lines. Call to be connected with a local plumbing professional.",
        "notes": [
            "Hard water leaves mineral buildup that can shorten the life of a water heater and clog faucet aerators and shower heads.",
            "Many homes sit on slab foundations. A warm spot on the floor or a water bill that jumps is worth describing on the call.",
            "Drain outdoor spigots and disconnect garden hoses before a freeze, and know where the main shutoff is.",
        ],
        "focus": "water heater scale, slab leaks, and frozen outdoor lines",
    },
    "alexandria-va": {
        "intro": "Alexandria has many older homes, from early houses to garden apartments, and cold snaps can freeze pipes in exterior walls and crawl spaces. Call to be connected with a local plumbing professional.",
        "notes": [
            "Older homes may still have galvanized supply lines or cast-iron drains. Mention the age of the house if you know it.",
            "In a multi-unit building, water can reach the unit below. Check whether building management needs to know.",
            "Before a hard freeze, disconnect garden hoses and know where your main shutoff valve is.",
        ],
        "focus": "leaks in older homes, drain line problems, and freeze damage along exterior walls",
    },
    "mesa-az": {
        "intro": "Mesa's desert heat and hard water both show up in plumbing, from scale in water heaters to fixtures that stop flowing freely. Many homes sit on slab foundations. Call to be connected with a local plumbing professional.",
        "notes": [
            "Mineral buildup can clog faucet aerators and shower heads and leave sediment in a tank water heater.",
            "An unexplained jump in the water bill, or a warm spot on the floor, can point to a leak under the slab.",
            "In summer, water from outdoor or shallow lines can run hot for a while. That alone is not a leak.",
        ],
        "focus": "water heater sediment, slab leaks, and fixture clogs from mineral buildup",
    },
}
PLAN5 = {
    "arlington-va": (["Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Sewer lines", "Water heaters"],
                 {"Leaks": "In an Arlington apartment or stacked unit, note whether the leak is inside the unit or coming from a shared wall or ceiling.",
                  "Burst or frozen pipes": "During a cold snap, pipes in exterior walls and unheated spaces are the usual trouble spots."}),
    "greensboro-nc": (["Sewer lines", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Water heaters"],
                 {"Sewer lines": "In older Greensboro neighborhoods, roots in the sewer lateral are a frequent reason backups return.",
                  "Burst or frozen pipes": "A hard freeze can split an outdoor spigot even when indoor pipes are fine."}),
    "winston-salem-nc": (["Sewer lines", "Leaks", "Burst or frozen pipes", "Clogs and slow drains", "Water heaters"],
                 {"Sewer lines": "On a hilly Winston Salem lot, a long sewer lateral can hide a root intrusion or a break. Mention repeat backups.",
                  "Leaks": "Clay soil that shifts between wet and dry spells can stress buried supply lines."}),
    "harrisburg-pa": (["Burst or frozen pipes", "Clogs and slow drains", "Sewer lines", "Leaks", "Water heaters"],
                 {"Burst or frozen pipes": "In a Harrisburg cold snap, pipes in unheated basements and along outside walls are the usual trouble spots.",
                  "Clogs and slow drains": "Water coming up through a basement floor drain during spring rain is worth describing on the call."}),
    "new-haven-ct": (["Burst or frozen pipes", "Clogs and slow drains", "Leaks", "Sewer lines", "Water heaters"],
                 {"Burst or frozen pipes": "In a New Haven cold snap, pipes along outside walls and in unheated basements are the usual trouble spots.",
                  "Clogs and slow drains": "Older cast-iron drain lines can narrow on the inside over the decades."}),
    "fresno-ca": (["Water heaters", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Sewer lines"],
                 {"Water heaters": "In Fresno, hard water can leave sediment in the tank; note any rumbling or popping sounds.",
                  "Leaks": "For homes on a slab, describe any warm or damp spots on the floor and changes in the water bill."}),
    "alexandria-va": (["Leaks", "Burst or frozen pipes", "Clogs and slow drains", "Sewer lines", "Water heaters"],
                 {"Leaks": "Low pressure together with rusty water in an older Alexandria home can point to aging supply lines.",
                  "Burst or frozen pipes": "Before a hard freeze, disconnect garden hoses and know how to shut off the main."}),
    "mesa-az": (["Water heaters", "Leaks", "Clogs and slow drains", "Sewer lines", "Burst or frozen pipes"],
                 {"Water heaters": "Mesa's hard water can leave sediment in the tank; note any rumbling or popping sounds.",
                  "Leaks": "A slab leak can show up as a damp patch of flooring or a spike in the water bill."}),
}
SIB5 = {
    "arlington-va": ["alexandria-va", "baltimore-md", "boston-ma"],
    "greensboro-nc": ["winston-salem-nc", "raleigh-nc", "columbia-sc"],
    "winston-salem-nc": ["greensboro-nc", "raleigh-nc", "knoxville-tn"],
    "harrisburg-pa": ["baltimore-md", "new-haven-ct", "boston-ma"],
    "new-haven-ct": ["boston-ma", "harrisburg-pa", "baltimore-md"],
    "fresno-ca": ["sacramento-ca", "los-angeles-ca", "san-francisco-ca"],
    "alexandria-va": ["arlington-va", "baltimore-md", "boston-ma"],
    "mesa-az": ["phoenix-az", "las-vegas-nv", "san-diego-ca"],
}

LOCAL.update(LOCAL5)
ISSUE_PLAN.update(PLAN5)
SIBLINGS.update(SIB5)
# Earlier pages also link to batch 5 neighbours.
for _k, _v in [("phoenix-az", "mesa-az"), ("raleigh-nc", "greensboro-nc"), ("raleigh-nc", "winston-salem-nc"),
               ("baltimore-md", "arlington-va"), ("boston-ma", "new-haven-ct"),
               ("sacramento-ca", "fresno-ca")]:
    if _v not in SIBLINGS[_k]:
        SIBLINGS[_k].append(_v)

# Batch 6 (2026-10-16)
LOCAL6 = {
    "greenville-sc": {
        "intro": "Greenville sits in the Upstate foothills, with red clay soil, humid summers, and a mix of older mill-village homes and newer subdivisions. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay soil swells when wet and shrinks when dry, which can stress buried water and sewer lines.",
            "Roots from mature trees can get into older sewer laterals. Mention backups that keep returning.",
            "Winters are usually mild, but a hard freeze can split an outdoor spigot. Disconnect garden hoses beforehand.",
        ],
        "focus": "sewer laterals and root intrusion, buried-line stress from clay, and outdoor spigot freezes",
    },
    "long-beach-ca": {
        "intro": "Long Beach has many older homes and apartment buildings near the coast, where salt air and hard water both wear on pipes and fixtures. Call to be connected with a local plumbing professional.",
        "notes": [
            "Hard water leaves mineral buildup that can shorten the life of a water heater and clog aerators and shower heads.",
            "In an apartment building, water can reach the unit below. Check whether the owner or manager needs to know.",
            "Older homes may still have galvanized supply lines or cast-iron drains. Mention the age of the building if you know it.",
        ],
        "focus": "leaks in older buildings, water heater scale, and drain problems in apartments",
    },
    "durham-nc": {
        "intro": "Durham mixes older in-town houses with newer subdivisions on Piedmont clay, and humid summers with occasional hard freezes. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay that shifts between wet and dry spells can stress pipes under a slab and in the yard.",
            "Roots from yard and street trees can get into older sewer lines and cause backups that return.",
            "On a cold night, pipes in crawl spaces and along outside walls are more exposed. Know where the main shutoff is.",
        ],
        "focus": "clay-soil pipe stress, root-related sewer backups, and crawl-space leaks",
    },
    "spokane-wa": {
        "intro": "Spokane winters bring long stretches below freezing, and many homes have basements or crawl spaces where pipes and water heaters sit. Call to be connected with a local plumbing professional.",
        "notes": [
            "Pipes along exterior walls, in crawl spaces, and in unheated garages are more exposed on cold nights. Know where the main shutoff is.",
            "Disconnect garden hoses and drain outdoor spigots before the first hard freeze.",
            "Older neighborhoods may still have cast-iron or clay drain lines. Mention the age of the house if you know it.",
        ],
        "focus": "frozen and burst pipes, basement drain problems, and water heater outages in winter",
    },
    "fort-myers-fl": {
        "intro": "Fort Myers has a warm, humid climate, heavy summer rain, and many homes on slab foundations. Call to be connected with a local plumbing professional.",
        "notes": [
            "An unexplained jump in the water bill, or a warm or damp spot on the floor, can point to a leak under the slab.",
            "Heavy rain can overload drains and sewer lines. Describe where any backup appears.",
            "Hard water can leave mineral buildup in water heaters and fixtures.",
        ],
        "focus": "slab leaks, drain backups after heavy rain, and water heater sediment",
    },
    "stockton-ca": {
        "intro": "Stockton sits in the Central Valley, where hot, dry summers and hard water take a toll on water heaters and fixtures, and winter nights can still freeze outdoor lines. Call to be connected with a local plumbing professional.",
        "notes": [
            "Hard water leaves mineral buildup that can shorten the life of a water heater and clog faucet aerators and shower heads.",
            "Many homes sit on slab foundations. A warm spot on the floor or a water bill that jumps is worth describing on the call.",
            "Drain outdoor spigots and disconnect garden hoses before a freeze, and know where the main shutoff is.",
        ],
        "focus": "water heater scale, slab leaks, and frozen outdoor lines",
    },
    "overland-park-ks": {
        "intro": "Overland Park has cold winters, hot summers, and many homes with basements where supply lines, drains, and water heaters sit. Call to be connected with a local plumbing professional.",
        "notes": [
            "Pipes along exterior walls and in unfinished basements are more exposed on cold nights. Know where the main shutoff is.",
            "Heavy spring storms can send water toward basement floor drains. Describe where any water appears.",
            "Roots from mature trees can get into older sewer laterals and cause backups that return.",
        ],
        "focus": "winter pipe freezes, basement drain backups after storms, and water heater outages",
    },
    "santa-barbara-ca": {
        "intro": "Santa Barbara has many older homes between the mountains and the coast, and hard water and salt air both wear on pipes and fixtures. Call to be connected with a local plumbing professional.",
        "notes": [
            "Older homes may still have galvanized supply lines or cast-iron drains. Mention the age of the house if you know it.",
            "Hard water leaves mineral buildup in water heaters, aerators, and shower heads.",
            "Look for corrosion on exposed pipes and hose bibs, especially closer to the coast.",
        ],
        "focus": "leaks in older homes, water heater scale, and corroded exposed pipes",
    },
}
PLAN6 = {
    "greenville-sc": (["Sewer lines", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Water heaters"],
                 {"Sewer lines": "In older Greenville neighborhoods, roots in the sewer lateral are a frequent reason backups return.",
                  "Burst or frozen pipes": "A hard freeze can split an outdoor spigot even when indoor pipes are fine."}),
    "long-beach-ca": (["Leaks", "Water heaters", "Clogs and slow drains", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "In a Long Beach apartment, note whether the leak is inside the unit or coming from a shared wall or ceiling.",
                  "Water heaters": "Hard water can leave sediment in the tank; note any rumbling or popping sounds."}),
    "durham-nc": (["Sewer lines", "Leaks", "Burst or frozen pipes", "Clogs and slow drains", "Water heaters"],
                 {"Sewer lines": "In older Durham neighborhoods, roots in the sewer lateral can cause backups that keep returning.",
                  "Leaks": "Clay soil that shifts between wet and dry spells can stress buried supply lines."}),
    "spokane-wa": (["Burst or frozen pipes", "Water heaters", "Clogs and slow drains", "Leaks", "Sewer lines"],
                 {"Burst or frozen pipes": "In a Spokane cold snap, pipes in crawl spaces and along outside walls are the usual trouble spots.",
                  "Water heaters": "A water heater that quits in winter is worth calling about quickly."}),
    "fort-myers-fl": (["Leaks", "Clogs and slow drains", "Water heaters", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "For Fort Myers homes on a slab, describe any warm or damp spots on the floor and changes in the water bill.",
                  "Clogs and slow drains": "Drains that back up after heavy rain are worth describing on the call."}),
    "stockton-ca": (["Water heaters", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Sewer lines"],
                 {"Water heaters": "In Stockton, hard water can leave sediment in the tank; note any rumbling or popping sounds.",
                  "Leaks": "For homes on a slab, describe any warm or damp spots on the floor and changes in the water bill."}),
    "overland-park-ks": (["Burst or frozen pipes", "Clogs and slow drains", "Sewer lines", "Leaks", "Water heaters"],
                 {"Burst or frozen pipes": "In an Overland Park cold snap, pipes in unfinished basements and along outside walls are the usual trouble spots.",
                  "Clogs and slow drains": "Water coming up through a basement floor drain during a storm is worth describing on the call."}),
    "santa-barbara-ca": (["Leaks", "Water heaters", "Clogs and slow drains", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "Low pressure together with rusty water in an older Santa Barbara home can point to aging supply lines.",
                  "Water heaters": "Hard water can leave sediment in the tank; note any rumbling or popping sounds."}),
}
SIB6 = {
    "greenville-sc": ["columbia-sc", "knoxville-tn", "atlanta-ga"],
    "long-beach-ca": ["los-angeles-ca", "san-diego-ca", "santa-barbara-ca"],
    "durham-nc": ["raleigh-nc", "greensboro-nc", "winston-salem-nc"],
    "spokane-wa": ["boise-id", "portland-or", "salt-lake-city-ut"],
    "fort-myers-fl": ["miami-fl", "fort-lauderdale-fl", "west-palm-beach-fl"],
    "stockton-ca": ["sacramento-ca", "san-francisco-ca", "fresno-ca"],
    "overland-park-ks": ["kansas-city-mo", "oklahoma-city-ok", "dallas-tx"],
    "santa-barbara-ca": ["los-angeles-ca", "long-beach-ca", "fresno-ca"],
}

LOCAL.update(LOCAL6)
ISSUE_PLAN.update(PLAN6)
SIBLINGS.update(SIB6)
for _k, _v in [("columbia-sc", "greenville-sc"), ("los-angeles-ca", "long-beach-ca"), ("raleigh-nc", "durham-nc"),
               ("boise-id", "spokane-wa"), ("miami-fl", "fort-myers-fl"), ("sacramento-ca", "stockton-ca"),
               ("kansas-city-mo", "overland-park-ks")]:
    if _v not in SIBLINGS[_k]:
        SIBLINGS[_k].append(_v)

# Batch 7 (2026-10-19)
LOCAL7 = {
    "anaheim-ca": {
        "intro": "Anaheim has neighborhoods of mid-century tract homes alongside newer developments, many on slab foundations, and the area's hard water is tough on water heaters and fixtures. Call to be connected with a local plumbing professional.",
        "notes": [
            "Hard water leaves mineral buildup that can shorten the life of a water heater and clog faucet aerators and shower heads.",
            "An unexplained jump in the water bill, or a warm or damp spot on the floor, can point to a leak under the slab.",
            "Older homes may still have galvanized supply lines or cast-iron drains. Mention the age of the house if you know it.",
        ],
        "focus": "slab leaks, water heater scale, and aging supply lines",
    },
    "irvine-ca": {
        "intro": "Irvine is made up of planned neighborhoods with many condos and townhomes that share walls, and hard water wears on water heaters and fixtures over time. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a condo or townhome, a leak can reach a neighbor's unit. Check whether your association needs to know before work starts.",
            "Hard water leaves mineral buildup in water heaters, aerators, and shower heads.",
            "Many homes sit on slab foundations. A warm spot on the floor or a water bill that jumps is worth describing on the call.",
        ],
        "focus": "leaks in shared-wall homes, water heater scale, and slab leaks",
    },
    "riverside-ca": {
        "intro": "Riverside's hot, dry summers and hard water both show up in plumbing, and the city mixes older homes near downtown with newer tracts on slab foundations. Call to be connected with a local plumbing professional.",
        "notes": [
            "Mineral buildup can clog faucet aerators and shower heads and leave sediment in a tank water heater.",
            "An unexplained jump in the water bill, or a warm spot on the floor, can point to a leak under the slab.",
            "Roots from mature trees can get into older sewer laterals. Mention backups that keep returning.",
        ],
        "focus": "water heater sediment, slab leaks, and root-related sewer backups",
    },
    "waterbury-ct": {
        "intro": "Waterbury has many older homes and multi-family houses on hilly streets, and cold, wet winters are hard on pipes and drains. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a multi-family house, a leak can travel between floors. Let neighbors or the owner know if water is moving.",
            "Older homes may have cast-iron drain lines or older supply pipes. Mention the age of the house if you know it.",
            "On cold nights, pipes along exterior walls and in unheated basements are more exposed. Know where the main shutoff is.",
        ],
        "focus": "frozen pipes in older houses, drain problems in multi-family homes, and leaks between floors",
    },
    "allentown-pa": {
        "intro": "Allentown has many row homes and older houses with basements, and Lehigh Valley winters bring hard freezes that can catch pipes off guard. Call to be connected with a local plumbing professional.",
        "notes": [
            "In a row home, a leak can reach a shared wall. Mention whether water is showing up next door.",
            "Pipes in unheated basements and along outside walls are more exposed on cold nights. Know where the main shutoff is.",
            "Heavy rain can send water toward basement floor drains. Describe where any water appears.",
        ],
        "focus": "winter pipe freezes, basement drain backups, and leaks in older row homes",
    },
    "manchester-nh": {
        "intro": "Manchester winters are long and cold, and the city has many older multi-family buildings and homes with basements where pipes and water heaters sit. Call to be connected with a local plumbing professional.",
        "notes": [
            "Pipes along exterior walls, in basements, and in unheated porches are more exposed on cold nights. Know where the main shutoff is.",
            "Disconnect garden hoses and drain outdoor spigots before the first hard freeze.",
            "In a multi-unit building, water can reach the unit below. Check whether the owner or manager needs to know.",
        ],
        "focus": "frozen and burst pipes, water heater outages in winter, and leaks in multi-unit buildings",
    },
    "port-saint-lucie-fl": {
        "intro": "Port Saint Lucie has a warm, humid climate, heavy summer rain, and many homes on slab foundations. Call to be connected with a local plumbing professional.",
        "notes": [
            "Some homes in the area use septic systems. Say whether you are on septic or city sewer when you call.",
            "An unexplained jump in the water bill, or a warm or damp spot on the floor, can point to a leak under the slab.",
            "Heavy rain can overload drains and sewer lines. Describe where any backup appears.",
        ],
        "focus": "septic and sewer questions, slab leaks, and drain backups after heavy rain",
    },
    "athens-ga": {
        "intro": "Athens mixes older in-town houses under mature trees with newer homes on red clay soil, and humid summers with the occasional hard freeze. Call to be connected with a local plumbing professional.",
        "notes": [
            "Roots from mature trees can get into older sewer laterals and cause backups that return.",
            "Clay soil swells when wet and shrinks when dry, which can stress buried water and sewer lines.",
            "Winters are usually mild, but a hard freeze can split an outdoor spigot. Disconnect garden hoses beforehand.",
        ],
        "focus": "root-related sewer backups, buried-line stress from clay, and outdoor spigot freezes",
    },
}
PLAN7 = {
    "anaheim-ca": (["Leaks", "Water heaters", "Clogs and slow drains", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "For Anaheim homes on a slab, describe any warm or damp spots on the floor and changes in the water bill.",
                  "Water heaters": "Hard water can leave sediment in the tank; note any rumbling or popping sounds."}),
    "irvine-ca": (["Leaks", "Water heaters", "Clogs and slow drains", "Sewer lines", "Burst or frozen pipes"],
                 {"Leaks": "In an Irvine condo or townhome, note whether the leak is inside your unit or coming from a shared wall or ceiling.",
                  "Water heaters": "Hard water can leave sediment in the tank; note any rumbling or popping sounds."}),
    "riverside-ca": (["Water heaters", "Leaks", "Sewer lines", "Clogs and slow drains", "Burst or frozen pipes"],
                 {"Water heaters": "In Riverside, hard water can leave sediment in the tank; note any rumbling or popping sounds.",
                  "Leaks": "A slab leak can show up as a damp patch of flooring or a spike in the water bill."}),
    "waterbury-ct": (["Burst or frozen pipes", "Clogs and slow drains", "Leaks", "Sewer lines", "Water heaters"],
                 {"Burst or frozen pipes": "In a Waterbury cold snap, pipes along outside walls and in unheated basements are the usual trouble spots.",
                  "Clogs and slow drains": "Older cast-iron drain lines can narrow on the inside over the decades."}),
    "allentown-pa": (["Burst or frozen pipes", "Clogs and slow drains", "Leaks", "Sewer lines", "Water heaters"],
                 {"Burst or frozen pipes": "In an Allentown cold snap, pipes in unheated basements and along outside walls are the usual trouble spots.",
                  "Clogs and slow drains": "Water coming up through a basement floor drain during heavy rain is worth describing on the call."}),
    "manchester-nh": (["Burst or frozen pipes", "Water heaters", "Clogs and slow drains", "Leaks", "Sewer lines"],
                 {"Burst or frozen pipes": "In a Manchester cold snap, pipes in basements and along outside walls are the usual trouble spots.",
                  "Water heaters": "A water heater that quits in winter is worth calling about quickly."}),
    "port-saint-lucie-fl": (["Leaks", "Sewer lines", "Clogs and slow drains", "Water heaters", "Burst or frozen pipes"],
                 {"Leaks": "For Port Saint Lucie homes on a slab, describe any warm or damp spots on the floor and changes in the water bill.",
                  "Sewer lines": "If the home is on septic, slow drains throughout the house are worth mentioning on the call."}),
    "athens-ga": (["Sewer lines", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Water heaters"],
                 {"Sewer lines": "In older Athens neighborhoods, roots in the sewer lateral are a frequent reason backups return.",
                  "Burst or frozen pipes": "A hard freeze can split an outdoor spigot even when indoor pipes are fine."}),
}
SIB7 = {
    "anaheim-ca": ["irvine-ca", "riverside-ca", "long-beach-ca"],
    "irvine-ca": ["anaheim-ca", "long-beach-ca", "san-diego-ca"],
    "riverside-ca": ["anaheim-ca", "irvine-ca", "los-angeles-ca"],
    "waterbury-ct": ["new-haven-ct", "boston-ma", "harrisburg-pa"],
    "allentown-pa": ["harrisburg-pa", "new-haven-ct", "baltimore-md"],
    "manchester-nh": ["boston-ma", "waterbury-ct", "new-haven-ct"],
    "port-saint-lucie-fl": ["west-palm-beach-fl", "fort-lauderdale-fl", "fort-myers-fl"],
    "athens-ga": ["atlanta-ga", "marietta-ga", "greenville-sc"],
}

LOCAL.update(LOCAL7)
ISSUE_PLAN.update(PLAN7)
SIBLINGS.update(SIB7)
for _k, _v in [("long-beach-ca", "anaheim-ca"), ("los-angeles-ca", "riverside-ca"), ("san-diego-ca", "irvine-ca"),
               ("new-haven-ct", "waterbury-ct"), ("harrisburg-pa", "allentown-pa"), ("boston-ma", "manchester-nh"),
               ("west-palm-beach-fl", "port-saint-lucie-fl"), ("atlanta-ga", "athens-ga")]:
    if _v not in SIBLINGS[_k]:
        SIBLINGS[_k].append(_v)

# Batch 8 (2026-10-19)
LOCAL8 = {
    "silver-spring-md": {
        "intro": "Silver Spring mixes older brick houses and garden apartments with newer high-rise condos, and cold winters alternate with humid summers. Call to be connected with a local plumbing professional.",
        "notes": [
            "In an apartment or condo building, a leak can reach the unit below. Check whether the building manager needs to know.",
            "Older homes may have cast-iron drains or older supply pipes. Mention the age of the house if you know it.",
            "On cold nights, pipes along exterior walls and in unheated spaces are more exposed. Know where the main shutoff is.",
        ],
        "focus": "leaks in multi-unit buildings, aging drain lines, and winter pipe freezes",
    },
    "kansas-city-ks": {
        "intro": "Kansas City, Kansas has many older homes with basements, and the region's winters bring hard freezes while spring storms bring heavy rain. Call to be connected with a local plumbing professional.",
        "notes": [
            "Heavy rain can push water toward basement floor drains. Describe where any water appears.",
            "Pipes in unheated basements and crawl spaces are more exposed on cold nights. Know where the main shutoff is.",
            "Roots from mature trees can get into older sewer laterals. Mention backups that keep returning.",
        ],
        "focus": "basement drain backups, winter pipe freezes, and root-related sewer problems",
    },
    "ogden-ut": {
        "intro": "Ogden sits at the foot of the Wasatch range, with cold, snowy winters, older homes near downtown, and hard water across the area. Call to be connected with a local plumbing professional.",
        "notes": [
            "Hard water leaves mineral buildup that can shorten the life of a water heater and clog faucet aerators and shower heads.",
            "Pipes along exterior walls and in unheated spaces are more exposed on cold nights. Know where the main shutoff is.",
            "Disconnect garden hoses and drain outdoor spigots before the first hard freeze.",
        ],
        "focus": "frozen pipes, water heater scale from hard water, and outdoor spigot freezes",
    },
    "saint-cloud-mn": {
        "intro": "Saint Cloud winters are long and very cold, and many homes have basements where pipes, water heaters, and floor drains sit. Call to be connected with a local plumbing professional.",
        "notes": [
            "Pipes along exterior walls, in basements, and in unheated porches are more exposed on cold nights. Know where the main shutoff is.",
            "A water heater that quits in winter is worth calling about quickly.",
            "Spring snowmelt can push water toward basement floor drains. Describe where any water appears.",
        ],
        "focus": "frozen and burst pipes, water heater outages in winter, and basement drain backups",
    },
    "bethesda-md": {
        "intro": "Bethesda has many older single-family homes under mature trees, along with newer condos near the town center, and winters bring regular freezes. Call to be connected with a local plumbing professional.",
        "notes": [
            "Roots from mature trees can get into older sewer laterals and cause backups that return.",
            "In a condo building, a leak can reach the unit below. Check whether the building manager needs to know.",
            "On cold nights, pipes along exterior walls and in unheated spaces are more exposed. Know where the main shutoff is.",
        ],
        "focus": "root-related sewer backups, leaks in condo buildings, and winter pipe freezes",
    },
    "spartanburg-sc": {
        "intro": "Spartanburg has older mill-village houses alongside newer subdivisions, red clay soil, and humid summers with the occasional hard freeze. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay soil swells when wet and shrinks when dry, which can stress buried water and sewer lines.",
            "Some homes outside the city use septic systems. Say whether you are on septic or city sewer when you call.",
            "Winters are usually mild, but a hard freeze can split an outdoor spigot. Disconnect garden hoses beforehand.",
        ],
        "focus": "buried-line stress from clay, septic and sewer questions, and outdoor spigot freezes",
    },
    "fayetteville-nc": {
        "intro": "Fayetteville has many rental homes and newer subdivisions on sandy soil, hot humid summers, and heavy rain from passing storms. Call to be connected with a local plumbing professional.",
        "notes": [
            "Some homes in the area use septic systems. Say whether you are on septic or city sewer when you call.",
            "If you rent, let your landlord or property manager know about the problem as well.",
            "Heavy rain can overload drains and sewer lines. Describe where any backup appears.",
        ],
        "focus": "septic and sewer questions, drain backups after heavy rain, and leaks in rental homes",
    },
    "denton-tx": {
        "intro": "Denton mixes older homes near the square with fast-growing newer neighborhoods, many on slab foundations over clay soil, and summers are long and hot. Call to be connected with a local plumbing professional.",
        "notes": [
            "Clay soil shifts with dry and wet spells, which can stress slab foundations and the pipes under them.",
            "An unexplained jump in the water bill, or a warm or damp spot on the floor, can point to a leak under the slab.",
            "Winters are usually mild, but a hard freeze can catch exposed pipes. Know where the main shutoff is.",
        ],
        "focus": "slab leaks, pipe stress from shifting clay soil, and rare hard freezes",
    },
}
PLAN8 = {
    "silver-spring-md": (["Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Water heaters", "Sewer lines"],
                 {"Leaks": "In a Silver Spring apartment or condo, note whether the leak is inside your unit or coming from a ceiling or shared wall.",
                  "Clogs and slow drains": "Older cast-iron drain lines can narrow on the inside over the decades."}),
    "kansas-city-ks": (["Clogs and slow drains", "Burst or frozen pipes", "Sewer lines", "Leaks", "Water heaters"],
                 {"Clogs and slow drains": "In Kansas City, Kansas, water coming up through a basement floor drain during heavy rain is worth describing on the call.",
                  "Sewer lines": "In older neighborhoods, roots in the sewer lateral are a frequent reason backups return."}),
    "ogden-ut": (["Burst or frozen pipes", "Water heaters", "Leaks", "Clogs and slow drains", "Sewer lines"],
                 {"Burst or frozen pipes": "In an Ogden cold snap, pipes along outside walls and in unheated spaces are the usual trouble spots.",
                  "Water heaters": "Hard water can leave sediment in the tank; note any rumbling or popping sounds."}),
    "saint-cloud-mn": (["Burst or frozen pipes", "Water heaters", "Clogs and slow drains", "Leaks", "Sewer lines"],
                 {"Burst or frozen pipes": "In a Saint Cloud cold snap, pipes in basements and along outside walls are the usual trouble spots.",
                  "Water heaters": "A water heater that quits in winter is worth calling about quickly."}),
    "bethesda-md": (["Sewer lines", "Leaks", "Burst or frozen pipes", "Clogs and slow drains", "Water heaters"],
                 {"Sewer lines": "In older Bethesda neighborhoods, roots in the sewer lateral are a frequent reason backups return.",
                  "Leaks": "In a condo, note whether the leak is inside your unit or coming from a ceiling or shared wall."}),
    "spartanburg-sc": (["Sewer lines", "Leaks", "Clogs and slow drains", "Burst or frozen pipes", "Water heaters"],
                 {"Sewer lines": "If a Spartanburg-area home is on septic, slow drains throughout the house are worth mentioning on the call.",
                  "Burst or frozen pipes": "A hard freeze can split an outdoor spigot even when indoor pipes are fine."}),
    "fayetteville-nc": (["Sewer lines", "Clogs and slow drains", "Leaks", "Water heaters", "Burst or frozen pipes"],
                 {"Sewer lines": "If a Fayetteville-area home is on septic, slow drains throughout the house are worth mentioning on the call.",
                  "Clogs and slow drains": "After heavy rain, note whether more than one drain is backing up."}),
    "denton-tx": (["Leaks", "Sewer lines", "Water heaters", "Clogs and slow drains", "Burst or frozen pipes"],
                 {"Leaks": "For Denton homes on a slab, describe any warm or damp spots on the floor and changes in the water bill.",
                  "Sewer lines": "Shifting clay soil can stress buried sewer lines; mention backups that keep returning."}),
}
SIB8 = {
    "silver-spring-md": ["bethesda-md", "baltimore-md", "arlington-va"],
    "kansas-city-ks": ["kansas-city-mo", "overland-park-ks", "oklahoma-city-ok"],
    "ogden-ut": ["salt-lake-city-ut", "boise-id", "denver-co"],
    "saint-cloud-mn": ["kansas-city-mo", "dayton-oh", "columbus-oh"],
    "bethesda-md": ["silver-spring-md", "arlington-va", "alexandria-va"],
    "spartanburg-sc": ["greenville-sc", "columbia-sc", "greensboro-nc"],
    "fayetteville-nc": ["raleigh-nc", "durham-nc", "columbia-sc"],
    "denton-tx": ["dallas-tx", "fort-worth-tx", "arlington-tx"],
}

LOCAL.update(LOCAL8)
ISSUE_PLAN.update(PLAN8)
SIBLINGS.update(SIB8)
for _k, _v in [("baltimore-md", "silver-spring-md"), ("arlington-va", "bethesda-md"), ("kansas-city-mo", "kansas-city-ks"),
               ("overland-park-ks", "kansas-city-ks"), ("salt-lake-city-ut", "ogden-ut"), ("greenville-sc", "spartanburg-sc"),
               ("raleigh-nc", "fayetteville-nc"), ("dallas-tx", "denton-tx")]:
    if _v not in SIBLINGS[_k]:
        SIBLINGS[_k].append(_v)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def footer() -> str:
    return (
        "<footer>\n"
        f'    <p class="disclaimer">{DISCLAIMER}</p>\n'
        '    <p class="footer-meta">Zaptu · <a href="/plumbing/">Plumbing</a> · <a href="/privacy/">Privacy</a> · <a href="/llms.txt">llms.txt</a></p>\n'
        "  </footer>"
    )


SHORT = {"Leaks": "Leaks", "Clogs and slow drains": "Drain Clogs", "Water heaters": "Water Heaters",
         "Burst or frozen pipes": "Frozen Pipes", "Sewer lines": "Sewer Lines"}
TELL = {
    "Leaks": "Where the water shows up, whether it drips or sprays, and whether the water meter moves with every fixture off.",
    "Clogs and slow drains": "Which drains are slow, whether more than one backs up at the same time, and what you have already tried.",
    "Water heaters": "Whether the heater is gas or electric, roughly how old it is, and any noises or water at the base.",
    "Burst or frozen pipes": "Which faucets have no water, where that pipe runs (outside wall, crawl space, garage), and whether the main is shut off.",
    "Sewer lines": "Whether the home is on city sewer or septic, which fixtures back up, and any sewage odor.",
}


def seo_title(c: dict, lead: str, warm: bool) -> str:
    short = "Burst Pipes" if warm and lead == "Burst or frozen pipes" else SHORT[lead]
    name = f"{c['city']}, {c['abbr']}"
    for t in (f"Plumber in {name}: {short} and More | Zaptu", f"Plumber in {name}: {short} | Zaptu",
              f"Plumber in {name} | Zaptu"):
        if len(t) <= 65:
            return t
    return f"Plumber in {name}"


def seo_desc(c: dict, loc: dict) -> str:
    name = f"{c['city']}, {c['abbr']}"
    for d in (f"Plumbing trouble in {name}? Call {PHONE_DISPLAY} to connect with a local plumbing professional about {loc['focus']}. Zaptu does not do the work.",
              f"Plumbing trouble in {name}? Call {PHONE_DISPLAY} to connect with a local plumbing professional. Zaptu does not do the work."):
        if len(d) <= 160:
            return d
    return d


def city_faqs(c: dict, loc: dict, areas: list) -> list:
    city, name = c["city"], f"{c['city']}, {c['abbr']}"
    if areas:
        cover = f"Based on our partner's current ZIP code coverage, the same number also reaches participating plumbing professionals in {', '.join(areas[:6])}. Coverage can change."
    else:
        cover = f"Coverage follows our partner's current ZIP codes for the {city} area and can change. Have your ZIP code ready when you call."
    return [
        (f"How do I reach a plumber in {name}?",
         f"Call {PHONE_DISPLAY}. A call-routing partner connects you with a participating independent plumbing professional if one is available for your ZIP code. You place the call yourself."),
        (f"What plumbing problems do {city} homeowners call about?",
         f"Calls in the {city} area often involve {loc['focus']}. {loc['notes'][0]}"),
        (f"Which areas near {city} does this number cover?", cover),
        ("Does Zaptu do the plumbing work or set the cost?",
         "No. Zaptu does not perform plumbing work and is not part of the agreement. You discuss the work, timing, and any costs directly with the plumbing company."),
        ("What should I do before I call?",
         "If water is actively leaking, close the main water shutoff. Have your ZIP code and a short description ready. If you smell gas, leave the building and call your gas utility or 911 first."),
    ]


def jsonld(c: dict, url: str, title: str, desc: str, faqs: list | None = None) -> str:
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
    if faqs:
        data["@graph"].append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs
            ],
        })
    return json.dumps(data, indent=2)


def city_page(c: dict) -> str:
    loc = LOCAL[c["slug"]]
    name = f"{c['city']}, {c['abbr']}"
    url = f"https://zaptu.ai/plumbing/{c['slug']}/"
    order, extra = ISSUE_PLAN[c["slug"]]
    base = dict(ISSUES)
    warm = c["slug"] in {"miami-fl", "fort-lauderdale-fl", "phoenix-az", "los-angeles-ca", "las-vegas-nv", "san-diego-ca",
            "west-palm-beach-fl", "boca-raton-fl", "san-francisco-ca", "fresno-ca", "mesa-az", "long-beach-ca", "fort-myers-fl", "stockton-ca", "santa-barbara-ca",
            "anaheim-ca", "irvine-ca", "riverside-ca", "port-saint-lucie-fl"}
    label = lambda t: "Burst pipes" if warm and t == "Burst or frozen pipes" else t
    issues = "\n".join(
        f"        <li><strong>{esc(label(t))}.</strong> {esc(base[t])}" + (f" {esc(extra[t])}" if t in extra else "") + "</li>"
        for t in order
    )
    notes = "\n".join(f"        <li>{esc(n)}</li>" for n in loc["notes"])
    # Nearby place names come from coverage data. Skip any that collide with the
    # ad-copy blocklist (Star, Idaho matches \bstars?\b) so the page stays compliant.
    areas = [a for a in c["nearby_covered_areas"] if not re.search(r"\bstars?\b", a, re.I)]
    title = seo_title(c, order[0], warm)
    desc = seo_desc(c, loc)
    faqs = city_faqs(c, loc, areas)
    tell = "\n".join(f"        <li>{esc(TELL[t])}</li>" for t in order[:3])
    urgent = ["Water you cannot stop, even with the fixture valve closed.",
              "Sewage coming up through a drain or toilet.",
              "Water near outlets, panels, or light fixtures.",
              "No water at all to the house." if warm else "No water after a freeze, which can mean a frozen or split pipe."]
    urgent_html = "\n".join(f"        <li>{esc(u)}</li>" for u in urgent)
    faq_html = "\n".join(f"      <h3>{esc(q)}</h3>\n      <p>{esc(a)}</p>" for q, a in faqs)
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
{jsonld(c, url, title, desc, faqs)}
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
      <h2>What to tell the plumber</h2>
      <ul>
        <li>Your ZIP code, the type of home (house, condo, apartment), and its rough age if you know it.</li>
{tell}
      </ul>
    </section>

    <section>
      <h2>When to call right away</h2>
      <ul>
{urgent_html}
      </ul>
      <p>A slow drip or a single slow drain can usually wait for a time that suits you, but mention how long it has been going on.</p>
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

    <section class="faq">
      <h2>{esc(c['city'])} plumbing questions</h2>
{faq_html}
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

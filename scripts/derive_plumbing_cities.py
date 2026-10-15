"""Derive covered plumbing cities + nearby covered areas from TCC coverage CSVs.

Input (not committed): $ZAPTU_TCC_DATA_DIR/tcc-plumbing-*.csv
Default directory: /home/box/agent-data/shared/zaptu
Output: scripts/plumbing_cities.json

"Nearby areas" = other cities in the ZIP-level coverage file, same state, whose ZIPs
fall in the metro's 3-digit ZIP prefixes AND have Min >= $100. Nothing is invented.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

SHARED = Path(os.environ.get("ZAPTU_TCC_DATA_DIR", "/home/box/agent-data/shared/zaptu"))
OUT = Path(__file__).with_name("plumbing_cities.json")
MIN_REQUIRED = 100.0

# (city, state, abbr, slug, metro ZIP3 prefixes)
CANDIDATES = [
    # South Florida: split the shared 330 prefix by ZIP range (Miami-Dade vs Broward).
    ("Miami", "Florida", "FL", "miami-fl", ["331", "332", "33010-33018", "33030-33035", "33054-33056"]),
    ("Fort Lauderdale", "Florida", "FL", "fort-lauderdale-fl", ["333", "33004-33009", "33019-33029", "33060-33077"]),
    ("Denver", "Colorado", "CO", "denver-co", ["800", "801", "802"]),
    ("Atlanta", "Georgia", "GA", "atlanta-ga", ["300", "303"]),
    ("Dallas", "Texas", "TX", "dallas-tx", ["750", "751", "752", "753"]),
    ("Houston", "Texas", "TX", "houston-tx", ["770", "772", "773", "774", "775"]),
    ("Phoenix", "Arizona", "AZ", "phoenix-az", ["850", "852", "853"]),
    ("Los Angeles", "California", "CA", "los-angeles-ca",
     ["900", "902", "903", "904", "905", "906", "910", "911", "912", "913", "914", "915", "916"]),
    ("Las Vegas", "Nevada", "NV", "las-vegas-nv", ["889", "890", "891"]),
    ("Boston", "Massachusetts", "MA", "boston-ma", ["021", "022", "024"]),
    # Substitutes, in order
    ("San Diego", "California", "CA", "san-diego-ca", ["919", "920", "921"]),
    # Batch 2 (2026-10-12): next highest median Min, then most covered ZIPs.
    ("Boulder", "Colorado", "CO", "boulder-co", ["803", "80025-80027", "80455", "80466", "80481", "80503", "80510", "80540", "80544"]),
    ("Fort Collins", "Colorado", "CO", "fort-collins-co", ["805"]),
    ("Fort Worth", "Texas", "TX", "fort-worth-tx", ["760", "761"]),
    ("West Palm Beach", "Florida", "FL", "west-palm-beach-fl", ["33401-33426", "33435-33437", "33460-33474", "33480"]),
    ("Sacramento", "California", "CA", "sacramento-ca", ["942", "956", "957", "958"]),
    ("San Antonio", "Texas", "TX", "san-antonio-tx", ["780", "781", "782"]),
    ("Kansas City", "Missouri", "MO", "kansas-city-mo", ["640", "641"]),
    ("Oklahoma City", "Oklahoma", "OK", "oklahoma-city-ok", ["730", "731"]),
    ("San Francisco", "California", "CA", "san-francisco-ca", ["940", "941"]),
    ("Boca Raton", "Florida", "FL", "boca-raton-fl", ["33427-33434", "33441-33448", "33481-33499"]),
    # Batch 3 (2026-10-13)
    ("Memphis", "Tennessee", "TN", "memphis-tn", ["381", "375"]),
    ("Portland", "Oregon", "OR", "portland-or", ["972", "970"]),
    ("Salt Lake City", "Utah", "UT", "salt-lake-city-ut", ["841"]),
    ("Baltimore", "Maryland", "MD", "baltimore-md", ["212"]),
    # Batch 4 (2026-10-15): next highest median Min not yet live, then most covered ZIPs;
    # skipped Pompano Beach/Hollywood FL (already nearby areas on Fort Lauderdale), Fresno (by-zip median $2.50).
    ("Marietta", "Georgia", "GA", "marietta-ga", ["30060-30069", "30008", "30080-30082", "30101-30102", "30106", "30126-30127", "30144", "30152"]),
    ("Arlington", "Texas", "TX", "arlington-tx", ["76001-76019", "76021-76022", "76039-76040", "76063", "75050-75054"]),
    ("Dayton", "Ohio", "OH", "dayton-oh", ["453", "454"]),
    ("Columbus", "Ohio", "OH", "columbus-oh", ["430", "431", "432"]),
    ("Raleigh", "North Carolina", "NC", "raleigh-nc", ["275", "276"]),
    ("Boise", "Idaho", "ID", "boise-id", ["836", "837"]),
    ("Columbia", "South Carolina", "SC", "columbia-sc", ["290", "291", "292"]),
    ("Knoxville", "Tennessee", "TN", "knoxville-tn", ["377", "378", "379"]),
]
TARGET = 32
MAX_AREAS = 12


def in_metro(zip5: str, prefixes: list[str]) -> bool:
    for p in prefixes:
        if "-" in p:
            lo, hi = p.split("-")
            if lo <= zip5 <= hi:
                return True
        elif zip5.startswith(p):
            return True
    return False


def norm(name: str) -> str:
    return " ".join(w.capitalize() for w in name.strip().lower().split())


def main() -> None:
    top = {(r["City"], r["State"]): r for r in csv.DictReader(open(SHARED / "tcc-plumbing-top-paying-cities.csv"))}
    by_city = {(r["City"], r["State"]): r for r in csv.DictReader(open(SHARED / "tcc-plumbing-coverage-by-city.csv"))}
    zips = list(csv.DictReader(open(SHARED / "tcc-plumbing-coverage-by-zip.csv")))

    chosen, rejected = [], []
    for city, state, abbr, slug, prefixes in CANDIDATES:
        if len(chosen) >= TARGET:
            break
        own = [r for r in zips if norm(r["City"]) == city and r["State"] == state]
        mins = [float(r["Min"]) for r in own]
        med = median(mins) if mins else 0.0
        covered = [r for r in own if float(r["Min"]) >= MIN_REQUIRED]
        in_top = (city, state) in top
        if not own or med < MIN_REQUIRED or not in_top:
            rejected.append({
                "city": city, "state": abbr, "median_min": med,
                "zips": len(own), "zips_ge_100": len(covered), "in_top_paying": in_top,
                "by_city": by_city.get((city, state)),
            })
            continue
        areas = Counter()
        for r in zips:
            if r["State"] != state or not in_metro(r["Zip"], prefixes):
                continue
            name = norm(r["City"])
            if name == city or float(r["Min"]) < MIN_REQUIRED:
                continue
            areas[name] += 1
        chosen.append({
            "city": city, "state": state, "abbr": abbr, "slug": slug,
            "median_min": med, "max_min": max(mins), "zips": len(own),
            "zips_ge_100": len(covered), "buyers": int(top[(city, state)]["buyers"]),
            "zip_areas": prefixes,
            "nearby_covered_areas": [a for a, _ in areas.most_common(MAX_AREAS)],
        })

    OUT.write_text(json.dumps({"min_required": MIN_REQUIRED, "cities": chosen, "rejected": rejected}, indent=2) + "\n")
    for c in chosen:
        print(f"{c['city']}, {c['abbr']}: median Min ${c['median_min']:.2f}, {c['zips_ge_100']}/{c['zips']} ZIPs >= $100, "
              f"buyers {c['buyers']}, areas {c['nearby_covered_areas']}")
    for r in rejected:
        print("REJECTED", r)


if __name__ == "__main__":
    main()

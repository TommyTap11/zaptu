"""Derive covered plumbing cities + nearby covered areas from TCC coverage CSVs.

Input (not committed): /home/box/agent-data/shared/zaptu/tcc-plumbing-*.csv
Output: scripts/plumbing_cities.json

"Nearby areas" = other cities in the ZIP-level coverage file, same state, whose ZIPs
fall in the metro's 3-digit ZIP prefixes AND have Min >= $100. Nothing is invented.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

SHARED = Path("/home/box/agent-data/shared/zaptu")
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
    ("San Antonio", "Texas", "TX", "san-antonio-tx", ["780", "781", "782"]),
    ("Boca Raton", "Florida", "FL", "boca-raton-fl", ["334"]),
]
TARGET = 10
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

#!/usr/bin/env python3
"""Check or update web/dashboard/polyares.json, the Polyares numbers shown on the private dashboard.

Polyares has no API hooked up, so sold forms, sold calls and revenue are copied by hand from
app.polyares.com/dashboard/leads. This script keeps that file honest: whole non-negative counts,
a dated as_of, and no consumer details (names, phones, emails, addresses) in lead rows.

  python3 scripts/polyares_numbers.py --check
  python3 scripts/polyares_numbers.py --set FORMS CALLS REVENUE --as-of 2026-11-04T09:00:00-05:00
  python3 scripts/polyares_numbers.py --number-status "Pest control" Live
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "web" / "dashboard" / "polyares.json"
LEAD_KEYS = {"date", "kind", "service", "city", "payout_usd"}
LEAD_KINDS = {"form", "call"}


def _count_ok(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _money_ok(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    for key in ("sold_forms", "sold_calls"):
        if not _count_ok(data.get(key)):
            errors.append(f"{key} must be a whole number >= 0")
    if not _money_ok(data.get("revenue_usd")):
        errors.append("revenue_usd must be a number >= 0")
    try:
        when = datetime.fromisoformat(str(data.get("as_of")))
        if when.tzinfo is None:
            errors.append("as_of needs a UTC offset, e.g. -05:00")
    except ValueError:
        errors.append("as_of must be an ISO date-time, e.g. 2026-11-03T09:20:00-05:00")
    if not str(data.get("source", "")).strip():
        errors.append("source must say where the numbers came from")
    leads = data.get("leads")
    if not isinstance(leads, list):
        errors.append("leads must be a list")
        leads = []
    for i, lead in enumerate(leads):
        if not isinstance(lead, dict):
            errors.append(f"leads[{i}] must be an object")
            continue
        extra = set(lead) - LEAD_KEYS
        if extra:
            errors.append(f"leads[{i}] has keys not allowed (no consumer details): {sorted(extra)}")
        if lead.get("kind") not in LEAD_KINDS:
            errors.append(f"leads[{i}].kind must be 'form' or 'call'")
        if not _money_ok(lead.get("payout_usd")):
            errors.append(f"leads[{i}].payout_usd must be a number >= 0")
    if isinstance(data.get("leads"), list) and _count_ok(data.get("sold_forms")) and _count_ok(data.get("sold_calls")):
        if len(leads) > data["sold_forms"] + data["sold_calls"]:
            errors.append("more lead rows than sold_forms + sold_calls")
    for i, n in enumerate(data.get("call_numbers") or []):
        if not all(str(n.get(k, "")).strip() for k in ("service", "number", "status")):
            errors.append(f"call_numbers[{i}] needs service, number and status")
    return errors


def load(path: Path = PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(data: dict, path: Path = PATH) -> None:
    errors = validate(data)
    if errors:
        raise ValueError("; ".join(errors))
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def set_numbers(data: dict, forms: int, calls: int, revenue: float, as_of: str) -> dict:
    out = dict(data)
    out.update(sold_forms=forms, sold_calls=calls, revenue_usd=round(float(revenue), 2), as_of=as_of)
    return out


def set_number_status(data: dict, service: str, status: str) -> dict:
    out = dict(data)
    nums = [dict(n) for n in out.get("call_numbers") or []]
    hits = [n for n in nums if n.get("service", "").lower() == service.lower()]
    if not hits:
        raise ValueError(f"no call number for service {service!r}")
    for n in hits:
        n["status"] = status
    out["call_numbers"] = nums
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set", nargs=3, metavar=("FORMS", "CALLS", "REVENUE"))
    ap.add_argument("--as-of")
    ap.add_argument("--number-status", nargs=2, metavar=("SERVICE", "STATUS"))
    args = ap.parse_args(argv)
    data = load()
    if args.set:
        if not args.as_of:
            ap.error("--set needs --as-of")
        data = set_numbers(data, int(args.set[0]), int(args.set[1]), float(args.set[2]), args.as_of)
    if args.number_status:
        data = set_number_status(data, *args.number_status)
    errors = validate(data)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.set or args.number_status:
        save(data)
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Price small objects across S3 storage classes, straight from the AWS price list.

Every price printed here is read from the published offer file for us-east-1
(its publication date is printed first), and every figure follows from the
object count and size on the command line. Nothing is typed in by hand.

    python3 scripts/tiering-cost-model.py --objects 1000000 --size 8KB

The 128 KB threshold shows up three times and never the same way:

  * Standard-IA, One Zone-IA and Glacier Instant Retrieval bill every object of
    less than 128 KB as if it were 128 KB (the "minimum billable object size").
  * A lifecycle transition skips objects smaller than 128 KB by default, so a
    rule written without a size filter leaves them where they are.
  * Intelligent-Tiering never tiers an object below 128 KB and does not charge
    the monitoring fee on it either, so a small object costs exactly what it
    costs in S3 Standard.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

PRICE_LIST_URL = (
    "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json"
)
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache", "s3-us-east-1.json")
GIB = 1024**3
MIN_BILLABLE = 128 * 1024  # 131,072 bytes

# usagetype -> (label, has 128 KB minimum, is a storage price per GB-month)
STORAGE = {
    "TimedStorage-ByteHrs": ("S3 Standard", False),
    "TimedStorage-SIA-ByteHrs": ("Standard-IA", True),
    "TimedStorage-ZIA-ByteHrs": ("One Zone-IA", True),
    "TimedStorage-GIR-ByteHrs": ("Glacier Instant Retrieval", True),
    "TimedStorage-INT-FA-ByteHrs": ("Intelligent-Tiering, Frequent Access", False),
    "TimedStorage-INT-IA-ByteHrs": ("Intelligent-Tiering, Infrequent Access", False),
}


def load_price_list(path: str | None) -> dict:
    if path:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        urllib.request.urlretrieve(PRICE_LIST_URL, CACHE)
    with open(CACHE, encoding="utf-8") as fh:
        return json.load(fh)


def extract(offer: dict) -> dict[str, float]:
    """usagetype -> price, plus the transition prices per request, in USD."""
    out: dict[str, float] = {}
    ondemand = offer["terms"]["OnDemand"]
    for sku, product in offer["products"].items():
        usage = product["attributes"].get("usagetype") or ""
        dims = [d for t in ondemand.get(sku, {}).values() for d in t["priceDimensions"].values()]
        if not dims:
            continue
        price = float(dims[0]["pricePerUnit"]["USD"])
        if usage in STORAGE or usage in ("Monitoring-Automation-INT", "EarlyDelete-SIA"):
            out[usage] = price
        for d in dims:
            desc = d["description"]
            if "transitions to" in desc:
                if "Standard-Infrequent Access" in desc:
                    out["TRANSITION_STANDARD_IA"] = float(d["pricePerUnit"]["USD"])
                elif "One Zone-Infrequent Access" in desc:
                    out["TRANSITION_ONEZONE_IA"] = float(d["pricePerUnit"]["USD"])
                elif "Glacier Instant Retrieval" in desc:
                    out["TRANSITION_GLACIER_IR"] = float(d["pricePerUnit"]["USD"])
                elif "Intelligent Tiering" in desc:
                    out["TRANSITION_INTELLIGENT_TIERING"] = float(d["pricePerUnit"]["USD"])
    return out


def parse_size(text: str) -> int:
    t = text.strip().upper()
    for suffix, mult in (("KIB", 1024), ("MIB", 1024**2), ("GIB", 1024**3),
                         ("KB", 1000), ("MB", 1000**2), ("GB", 1000**3), ("B", 1)):
        if t.endswith(suffix):
            return int(float(t[: -len(suffix) or None]) * mult)
    return int(t)


def storage_cost(unit_price: float, objects: int, size: int, minimum: bool) -> float:
    billed = objects * (max(size, MIN_BILLABLE) if minimum else size)
    return billed / GIB * unit_price


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", type=int, default=1_000_000)
    ap.add_argument("--size", default="8KB", help="8KB, 8KiB, 100KB, 1MB ...")
    ap.add_argument("--price-list", default=None)
    args = ap.parse_args()

    offer = load_price_list(args.price_list)
    p = extract(offer)
    n, size = args.objects, parse_size(args.size)
    actual_gib = n * size / GIB
    billed_gib = n * max(size, MIN_BILLABLE) / GIB

    print(f"price list : {offer.get('publicationDate')}  (us-east-1, offer {offer.get('version')})")
    print(f"workload   : {n:,} objects of {size:,} bytes = {actual_gib:,.2f} GiB of real bytes")
    if size < MIN_BILLABLE:
        print(f"billed size: {MIN_BILLABLE:,} bytes each in IA / One Zone-IA / Glacier IR "
              f"= {billed_gib:,.2f} GiB, i.e. {billed_gib / actual_gib:.0f}x the data")
    print()

    rows = [
        ("S3 Standard", "TimedStorage-ByteHrs", "TRANSITION_STANDARD_IA"),
        ("Standard-IA", "TimedStorage-SIA-ByteHrs", "TRANSITION_STANDARD_IA"),
        ("One Zone-IA", "TimedStorage-ZIA-ByteHrs", "TRANSITION_ONEZONE_IA"),
        ("Glacier Instant Retrieval", "TimedStorage-GIR-ByteHrs", "TRANSITION_GLACIER_IR"),
    ]
    print("| storage class | $/GB-month | storage | transition requests | first month |")
    print("| --- | --- | --- | --- | --- |")
    for label, key, transition_key in rows:
        unit = p[key]
        storage = storage_cost(unit, n, size, STORAGE[key][1])
        # A bucket already in this class is not transitioning into it: the first
        # month only pays the transition fee when the objects arrive from Standard.
        transition = n * p[transition_key] if label != "S3 Standard" else 0.0
        trans_cell = f"${transition:,.2f}" if transition else "—"
        print(f"| {label} | {unit:.5f} | ${storage:,.2f} | {trans_cell} | ${storage + transition:,.2f} |")

    if size < MIN_BILLABLE:
        it = storage_cost(p["TimedStorage-INT-FA-ByteHrs"], n, size, False)
        print(f"| Intelligent-Tiering | {p['TimedStorage-INT-FA-ByteHrs']:.5f} | ${it:,.2f} | $0.00 | ${it:,.2f} |")
        print("\nIntelligent-Tiering is free to adopt here and saves nothing: objects under 128 KB are")
        print("never monitored, never tiered, and carry no monitoring and automation charge.")
    else:
        fee = n * p["Monitoring-Automation-INT"]
        it_ia = storage_cost(p["TimedStorage-INT-IA-ByteHrs"], n, size, False) + fee
        print(f"| Intelligent-Tiering (after 30 idle days) | {p['TimedStorage-INT-IA-ByteHrs']:.5f} "
              f"| ${it_ia:,.2f} | $0.00 | ${it_ia:,.2f} |")
        print(f"\n  monitoring and automation: ${fee:,.2f} for {n:,} objects "
              f"(${p['Monitoring-Automation-INT']:.7f} per object-month)")

    std, sia = p["TimedStorage-ByteHrs"], p["TimedStorage-SIA-ByteHrs"]
    saving_per_byte = (std - sia) / GIB
    crossover = MIN_BILLABLE * sia / std
    fee_object = p["Monitoring-Automation-INT"]
    print("\ncrossovers and paybacks, storage and request prices only:")
    print(f"  Standard-IA costs the same as S3 Standard at {crossover:,.0f} bytes "
          f"({crossover / 1024:,.1f} KiB) per object; below that the 128 KB minimum makes it dearer")
    if size < MIN_BILLABLE:
        waste = (billed_gib - actual_gib) * sia
        print(f"  the minimum-size charge alone is ${waste:,.2f} a month for these objects")
    for probe in (MIN_BILLABLE, 1024**2):
        months = p["TRANSITION_STANDARD_IA"] / (saving_per_byte * probe)
        print(f"  a {probe // 1024:>5,} KiB object repays its transition request in {months:,.2f} months")
    print(f"  the monitoring fee equals the Standard to IA saving at "
          f"{fee_object / saving_per_byte / 1024:,.0f} KiB per object")
    return 0


if __name__ == "__main__":
    sys.exit(main())

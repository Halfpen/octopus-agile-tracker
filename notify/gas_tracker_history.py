"""Compare Octopus Tracker gas prices with Flexible Octopus gas for one region.

Finds every Tracker product on sale now or at the reference dates, downloads its gas
unit rates and standing charges since FROM, and writes daily rows to a CSV.

Usage: python3 notify/gas_tracker_history.py FROM OUT.csv [REGION]
"""
import csv
import sys
from datetime import datetime, timezone

sys.path.insert(0, __import__("os").path.dirname(__file__))
from agile_notify import API, get_json  # noqa: E402

REFERENCE_DATES = ["2025-04-20", "2025-10-01", "2026-04-01", None]  # None = now


def products_at(when):
    url = f"{API}/products/?brand=OCTOPUS_ENERGY&page_size=100"
    if when:
        url += f"&available_at={when}T00:00Z"
    found = []
    while url:
        page = get_json(url)
        found += page["results"]
        url = page["next"]
    return found


def all_pages(url):
    rows = []
    while url:
        page = get_json(url)
        rows += page["results"]
        url = page["next"]
    return rows


def main():
    start, out = sys.argv[1], sys.argv[2]
    region = sys.argv[3] if len(sys.argv) > 3 else "G"
    wanted = {}
    for when in REFERENCE_DATES:
        for p in products_at(when):
            name = p.get("display_name", "")
            if ("Tracker" in name or name == "Flexible Octopus") and p.get("direction") != "EXPORT":
                wanted[p["code"]] = name
    print("products:", wanted)
    now = datetime.now(timezone.utc)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product", "name", "kind", "valid_from", "valid_to", "value_exc_vat", "value_inc_vat"])
        for code, name in sorted(wanted.items()):
            tariff = f"G-1R-{code}-{region}"
            for kind in ("standard-unit-rates", "standing-charges"):
                url = (f"{API}/products/{code}/gas-tariffs/{tariff}/{kind}/"
                       f"?period_from={start}T00:00Z&period_to={now:%Y-%m-%dT%H:%MZ}&page_size=1500")
                try:
                    rows = all_pages(url)
                except Exception as e:
                    print(code, kind, e)
                    continue
                for r in rows:
                    w.writerow([code, name, kind, r["valid_from"], r["valid_to"], r["value_exc_vat"], r["value_inc_vat"]])
                print(code, kind, len(rows))


if __name__ == "__main__":
    main()

"""Download historical Agile unit rates (exc. VAT) to a CSV for offline analysis.

Usage: python3 notify/fetch_history.py FROM TO OUT.csv   (dates as YYYY-MM-DD, UTC)
TARIFF env var picks the tariff (default E-1R-AGILE-24-10-01-G).
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from agile_notify import API, get_json  # noqa: E402


def main():
    start, end, out = sys.argv[1:4]
    tariff = os.environ.get("TARIFF") or "E-1R-AGILE-24-10-01-G"
    product = "-".join(tariff.split("-")[2:-1])
    url = (f"{API}/products/{product}/electricity-tariffs/{tariff}/standard-unit-rates/"
           f"?period_from={start}T00:00Z&period_to={end}T00:00Z&page_size=1500")
    rows = []
    while url:
        page = get_json(url)
        rows += page["results"]
        url = page["next"]
    rows.sort(key=lambda r: r["valid_from"])
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["valid_from", "valid_to", "value_exc_vat"])
        for r in rows:
            w.writerow([r["valid_from"], r["valid_to"], r["value_exc_vat"]])
    print(f"{len(rows)} rates written to {out}")


if __name__ == "__main__":
    main()

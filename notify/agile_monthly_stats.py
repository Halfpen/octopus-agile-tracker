"""Monthly statistics of Agile unit rates (exc. VAT) for one region since Agile launched.

For each month it finds the Agile product on sale at the start of that month, downloads
that product's rates for the month and writes one CSV row of averages.

Usage: python3 notify/agile_monthly_stats.py OUT.csv [REGION]
"""
import csv
import statistics
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, __import__("os").path.dirname(__file__))
from agile_notify import API, get_json  # noqa: E402

LONDON = ZoneInfo("Europe/London")


def agile_product_at(when):
    url = f"{API}/products/?brand=OCTOPUS_ENERGY&available_at={when:%Y-%m-%dT%H:%MZ}&page_size=100"
    codes = []
    while url:
        page = get_json(url)
        codes += [p["code"] for p in page["results"] if p["code"].startswith("AGILE") and "OUTGOING" not in p["code"]]
        url = page["next"]
    # prefer the plain import product over flex/variants
    codes.sort(key=lambda c: ("FLEX" in c or "BB" in c, c))
    return codes[0] if codes else None


def month_rates(product, region, start, end):
    tariff = f"E-1R-{product}-{region}"
    url = (f"{API}/products/{product}/electricity-tariffs/{tariff}/standard-unit-rates/"
           f"?period_from={start:%Y-%m-%dT%H:%MZ}&period_to={end:%Y-%m-%dT%H:%MZ}&page_size=1500")
    rows = []
    while url:
        page = get_json(url)
        rows += page["results"]
        url = page["next"]
    return rows


def main():
    out = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "G"
    year, month = 2018, 3
    now = datetime.now(timezone.utc)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "product", "slots", "avg", "night_23_06", "peak_16_19", "min", "max", "negative_slots"])
        while datetime(year, month, 1, tzinfo=timezone.utc) < now:
            start = datetime(year, month, 1, tzinfo=timezone.utc)
            ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
            end = min(datetime(ny, nm, 1, tzinfo=timezone.utc), now)
            try:
                product = agile_product_at(start.replace(day=2))
                rows = month_rates(product, region, start, end) if product else []
            except Exception as e:  # keep going; one bad month should not stop the history
                print(f"{year}-{month:02d}: {e}")
                product, rows = None, []
            if rows:
                vals, night, peak = [], [], []
                for r in rows:
                    t = datetime.fromisoformat(r["valid_from"].replace("Z", "+00:00")).astimezone(LONDON)
                    hm = t.strftime("%H:%M")
                    v = r["value_exc_vat"]
                    vals.append(v)
                    if hm >= "23:00" or hm < "06:00":
                        night.append(v)
                    if "16:00" <= hm < "19:00":
                        peak.append(v)
                w.writerow([f"{year}-{month:02d}", product, len(vals), round(statistics.mean(vals), 2),
                            round(statistics.mean(night), 2), round(statistics.mean(peak), 2),
                            min(vals), max(vals), sum(v < 0 for v in vals)])
                print(f"{year}-{month:02d} {product} {len(vals)} slots")
            year, month = ny, nm


if __name__ == "__main__":
    main()

"""List Octopus fixed tariffs on sale now with their current gas rates for one region.

Usage: python3 notify/fixed_gas_offers.py OUT.csv [REGION]
"""
import csv
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from agile_notify import API, get_json  # noqa: E402


def main():
    out = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "G"
    url = f"{API}/products/?brand=OCTOPUS_ENERGY&is_business=false&page_size=100"
    products = []
    while url:
        page = get_json(url)
        products += page["results"]
        url = page["next"]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "term_months", "is_variable", "fuel", "unit_inc_vat", "standing_inc_vat", "exit_fees"])
        for p in products:
            if p.get("is_variable") or p.get("direction") == "EXPORT":
                continue
            detail = get_json(p["links"][0]["href"]) if p.get("links") else get_json(f"{API}/products/{p['code']}/")
            for fuel in ("single_register_gas_tariffs", "single_register_electricity_tariffs"):
                t = detail.get(fuel, {}).get(f"_{region}", {}).get("direct_debit_monthly")
                if not t:
                    continue
                w.writerow([p["code"], p.get("display_name"), p.get("term"), p.get("is_variable"), fuel.split("_")[2],
                            t.get("standard_unit_rate_inc_vat"), t.get("standing_charge_inc_vat"),
                            t.get("exit_fees")])
                print(p["code"], p.get("display_name"), fuel, t.get("standard_unit_rate_inc_vat"))


if __name__ == "__main__":
    main()

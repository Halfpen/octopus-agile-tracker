"""Schedule ntfy push notifications for upcoming cheap Agile Octopus slots.

Runs after Octopus publishes the next day's prices (around 16:00 UK time).
Each cheap window gets one notification, delivered by ntfy at the window's
start (minus LEAD_MIN), plus one summary sent straight away.

Environment:
  NTFY_TOPIC   required, the ntfy topic your phone subscribes to
  NTFY_SERVER  default https://ntfy.sh
  THRESHOLD    p/kWh incl. VAT; slots below this count as cheap (default 10)
  LEAD_MIN     minutes before a window to notify (default 5)
  VAT_PERCENT  electricity VAT applied to value_exc_vat (default 0)
  TARIFF       default E-1R-AGILE-24-10-01-G (North West)
  APP_URL      link opened when a notification is tapped
  CHARGE_HOURS length of the Tesla charging block to look for (default 4)
  SUPERCHARGER_P  local Supercharger price, p/kWh incl. VAT, to compare against (default 25)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
API = "https://api.octopus.energy/v1"


def env(name, default=None):
    value = os.environ.get(name, "").strip()
    return value if value else default


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "agile-notify"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_rates(tariff, start, end, vat):
    product = "-".join(tariff.split("-")[2:-1])
    url = (f"{API}/products/{product}/electricity-tariffs/{tariff}/standard-unit-rates/"
           f"?period_from={start:%Y-%m-%dT%H:%MZ}&period_to={end:%Y-%m-%dT%H:%MZ}&page_size=1500")
    rows = []
    while url:
        page = get_json(url)
        rows += page["results"]
        url = page["next"]
    slots = [{
        "start": datetime.fromisoformat(r["valid_from"].replace("Z", "+00:00")),
        "end": datetime.fromisoformat(r["valid_to"].replace("Z", "+00:00")),
        "p": r["value_exc_vat"] * (1 + vat / 100),
    } for r in rows]
    return sorted(slots, key=lambda s: s["start"])


def new_batch(slots, now):
    """Slots in the newest 24h of published prices, or [] if tomorrow isn't out yet."""
    if not slots:
        return []
    end = max(s["end"] for s in slots)
    batch_start = end - timedelta(hours=24)
    if batch_start < now:
        return []
    return [s for s in slots if s["start"] >= batch_start]


def cheap_windows(slots, threshold):
    windows = []
    for s in slots:
        if s["p"] >= threshold:
            continue
        if windows and windows[-1][-1]["end"] == s["start"]:
            windows[-1].append(s)
        else:
            windows.append([s])
    return windows


def cheapest_block(slots, n):
    """Cheapest run of n consecutive slots, as a list, or None."""
    best, best_avg = None, None
    for i in range(len(slots) - n + 1):
        block = slots[i:i + n]
        if any(block[j]["start"] != block[j - 1]["end"] for j in range(1, n)):
            continue
        avg = sum(s["p"] for s in block) / n
        if best_avg is None or avg < best_avg:
            best, best_avg = block, avg
    return best


def hm(dt):
    return dt.astimezone(LONDON).strftime("%H:%M")


def day_label(dt):
    local = dt.astimezone(LONDON)
    return f"{local.day}/{local.month}（{'一二三四五六日'[local.weekday()]}）"


def describe(window):
    prices = [s["p"] for s in window]
    avg = sum(prices) / len(prices)
    return (f"{hm(window[0]['start'])}–{hm(window[-1]['end'])}",
            f"平均 {avg:.2f}p，最低 {min(prices):.2f}p")


def build_messages(batch, threshold, lead_min, now, charge_hours=4, supercharger_p=25):
    windows = cheap_windows(batch, threshold)
    block = cheapest_block(batch, int(charge_hours * 2))
    cheapest = min(batch, key=lambda s: s["p"])
    negative = sum(1 for s in batch if s["p"] < 0)
    lines = [f"最平：{hm(cheapest['start'])} {cheapest['p']:.2f}p"]
    if negative:
        lines.append(f"負電價時段：{negative} 個（用電有錢收）")
    if windows:
        lines.append(f"低於 {threshold:g}p 嘅時段：")
        lines += [f"• {span}  {stats}" for span, stats in map(describe, windows)]
    else:
        lines.append(f"冇時段低於 {threshold:g}p")
    if block:
        block_avg = sum(s["p"] for s in block) / len(block)
        span = f"{hm(block[0]['start'])}–{hm(block[-1]['end'])}"
        lines.append(f"最平連續 {charge_hours:g} 小時充電：{span} 平均 {block_avg:.2f}p")
        if not windows:
            gap = supercharger_p - block_avg
            lines.append(f"超充站大約 {supercharger_p:g}p → "
                         + (f"喺屋企充平 {gap:.1f}p/kWh" if gap >= 0 else f"去超充平 {-gap:.1f}p/kWh"))
    messages = [{
        "title": f"{day_label(batch[-1]['start'])} " + ("Agile 電價已公佈" if windows else "冇平電"),
        "message": "\n".join(lines),
        "tags": ["zap"] if windows else ["warning"],
    }]
    # No cheap window: remind at the start of the best charging block instead.
    if block and not windows and block_avg < supercharger_p:
        at = block[0]["start"] - timedelta(minutes=lead_min)
        msg = {"title": f"Tesla 充電時段開始：{span}",
               "message": f"平均 {block_avg:.2f}p（超充大約 {supercharger_p:g}p）",
               "tags": ["electric_plug"]}
        if at > now + timedelta(seconds=30):
            msg["delay"] = str(int(at.timestamp()))
        messages.append(msg)
    for w in windows:
        span, stats = describe(w)
        at = w[0]["start"] - timedelta(minutes=lead_min)
        neg = min(s["p"] for s in w) < 0
        msg = {
            "title": f"{'負電價' if neg else '平電'}開始：{span}",
            "message": stats,
            "tags": ["moneybag" if neg else "battery"],
            "priority": 4 if neg else 3,
        }
        if at > now + timedelta(seconds=30):
            msg["delay"] = str(int(at.timestamp()))
        messages.append(msg)
    return messages


def publish(server, topic, msg, app_url):
    body = dict(msg, topic=topic)
    if app_url:
        body["click"] = app_url
    req = urllib.request.Request(server, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def main():
    dry_run = "--dry-run" in sys.argv
    test = "--test" in sys.argv
    topic = env("NTFY_TOPIC")
    if not topic and not dry_run:
        sys.exit("NTFY_TOPIC is not set. Add it under Settings → Secrets and variables → Actions.")
    server = env("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    app_url = env("APP_URL")

    if test:
        publish(server, topic, {"title": "Agile 通知測試", "message": "收到呢條就代表設定成功。", "tags": ["white_check_mark"]}, app_url)
        print("Test notification sent.")
        return

    threshold = float(env("THRESHOLD", "10"))
    lead_min = int(env("LEAD_MIN", "5"))
    vat = float(env("VAT_PERCENT", "0"))
    tariff = env("TARIFF", "E-1R-AGILE-24-10-01-G")
    now = datetime.now(timezone.utc)

    slots = fetch_rates(tariff, now - timedelta(hours=1), now + timedelta(hours=48), vat)
    batch = new_batch(slots, now)
    if not batch:
        print("Tomorrow's prices are not published yet.")
        return

    charge_hours = float(env("CHARGE_HOURS", "4"))
    supercharger_p = float(env("SUPERCHARGER_P", "25"))
    for msg in build_messages(batch, threshold, lead_min, now, charge_hours, supercharger_p):
        when = datetime.fromtimestamp(int(msg["delay"]), LONDON).strftime("%d/%m %H:%M") if "delay" in msg else "now"
        print(f"[{when}] {msg['title']} | {msg['message']}")
        if not dry_run:
            publish(server, topic, msg, app_url)

    marker = env("GITHUB_OUTPUT")
    if marker and not dry_run:
        with open(marker, "a") as f:
            f.write("sent=true\n")


if __name__ == "__main__":
    main()

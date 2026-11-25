#!/usr/bin/env python3
"""Fetch Wetherby Watches' public eBay feedback stats and latest live listings.

Reads two public eBay pages (no login needed):
  - feedback profile: https://www.ebay.co.uk/fdbk/feedback_profile/wetherbywatchesltd
  - eBay shop front, newest first: https://www.ebay.co.uk/str/wetherbywatches?_sop=10&rt=nc
Writes data.json next to this script. Exits non-zero (and keeps the old data.json)
if eBay blocks the request or the page layout changes, so stale-but-correct
images stay up rather than broken ones.
"""
import html, json, re, sys, os, datetime, subprocess, time, tempfile

SELLER = "wetherbywatchesltd"
STORE = "wetherbywatches"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
JAR = os.path.join(tempfile.gettempdir(), "ww_ebay_cookies.txt")
HERE = os.path.dirname(os.path.abspath(__file__))


def get(url):
    # curl copes better than urllib with eBay's chunked/compressed responses
    for attempt in range(4):
        r = subprocess.run(["curl", "-sL", "--compressed", "--max-time", "60", "-A", UA,
                            "-c", JAR, "-b", JAR, "-H", "Referer: https://www.ebay.co.uk/",
                            "-H", "Accept-Language: en-GB,en;q=0.9", "-H", "Accept: text/html,application/xhtml+xml",
                            "-w", "\n%{http_code}", url], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n")
        if code == "200":
            return body
        time.sleep(5 + attempt * 10)
    if code != "200":
        sys.exit(f"eBay returned HTTP {code} for {url} - keeping previous data.json")
    return body


def text_of(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", s, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", "\n", s))
    return [l.strip() for l in s.split("\n") if l.strip()]


def feedback():
    s = get(f"https://www.ebay.co.uk/fdbk/feedback_profile/{SELLER}?filter=feedback_page%3ARECEIVED_AS_SELLER&sort=TIME")
    lines = text_of(s)
    t = "\n".join(lines)
    out = {}
    m = re.search(SELLER + r"\n\(\n([\d,]+)\n\)", t)
    out["score"] = int(m.group(1).replace(",", ""))
    out["positive_pct"] = re.search(r"Positive Feedback \(last 12 months\): ([\d.]+%)", t).group(1)
    i = lines.index("Positive")
    out["positive"] = dict(zip(["1m", "6m", "12m"], map(int, lines[i + 1:i + 4])))
    i = lines.index("Neutral"); out["neutral_12m"] = int(lines[i + 3])
    i = lines.index("Negative"); out["negative_12m"] = int(lines[i + 3])
    dsr = {}
    for name in ["Accurate description", "Reasonable postage cost", "Delivery time", "Communication"]:
        m = re.search(re.escape(name) + r"\n\((\d+)\)\nAverage rating of ([\d.]+) out of 5", t)
        if m:
            dsr[name] = {"count": int(m.group(1)), "avg": float(m.group(2))}
    out["dsr"] = dsr
    m = re.search(r"Member since: ([^\n]+?) in", t); out["member_since"] = m.group(1) if m else ""
    out["top_rated"] = "eBay Top-rated seller" in t
    # recent positive buyer comments (newest first), short ones only
    comments = []
    for row in re.findall(r"<tr data-feedback-id=\d+>(.*?)</tr>", s, flags=re.S):
        if "data-test-type=positive" not in row:
            continue
        m = re.search(r'class=card__comment><span aria-label="([^"]+)"', row)
        if not m:
            continue
        c = html.unescape(m.group(1)).strip()
        if 25 <= len(c) <= 170 and "automated" not in c.lower():
            comments.append(c)
    out["recent_comments"] = comments[:3]
    return out


def listings():
    s = get(f"https://www.ebay.co.uk/str/{STORE}?_sop=10&rt=nc")
    items = []
    for part in s.split("class=str-item-card__link")[1:]:
        pre = part
        img = re.search(r"i\.ebayimg\.com/images/g/([A-Za-z0-9_-]+)/", pre)
        title = re.search(r"str-item-card__property-title[^>]*><span[^>]*>([^<]+)</span>", pre)
        price = re.search(r"property-displayPrice\">([^<]+)<", pre)
        if not (img and title):
            continue
        items.append({"title": html.unescape(title.group(1)).strip(),
                      "price": html.unescape(price.group(1)).strip() if price else "",
                      "image": f"https://i.ebayimg.com/images/g/{img.group(1)}/s-l800.jpg"})
    ids = re.findall(r"<a href=https://www\.ebay\.co\.uk/itm/(\d{12})[^>]*class=str-item-card__link", s)
    for it, iid in zip(items, ids):
        it["item_id"] = iid
    return items


def main():
    data = {"fetched_at": datetime.datetime.now().astimezone().isoformat(timespec="minutes")}
    data["feedback"] = feedback()
    data["listings"] = listings()
    if len(data["listings"]) < 3 or data["feedback"]["score"] < 100:
        sys.exit("Unexpected page content - keeping previous data.json")
    with open(os.path.join(HERE, "data.json"), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"OK: score {data['feedback']['score']}, {len(data['listings'])} live listings")


if __name__ == "__main__":
    main()

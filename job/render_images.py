#!/usr/bin/env python3
"""Turn data.json into the images the eBay template points at.

Output folder (default ./public) gets:
  feedback.png          - live feedback summary banner
  card-1.jpg..card-6.jpg - newest six live listings (photo, title, price)
  thumb-1.jpg..thumb-6.jpg - small square photos for the header strip
Upload the whole folder, unchanged file names, to the image host each time.
"""
import io, json, os, sys, datetime, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "public")
N_CARDS = 6
BG, PANEL, LINE, GOLD, GOLD2, TEXT, MUTED = "#050505", "#111111", "#4a3b20", "#c4a45f", "#e2c777", "#f7f2e8", "#c7bda9"
F = "/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf"
def font(size, bold=False): return ImageFont.truetype(F % ("Bold" if bold else "Regular"), size)


def fetch_image(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "40", url], capture_output=True)
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def wrap(draw, text, fnt, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines and cur:
        lines.append(cur)
    used = " ".join(lines)
    if len(used) < len(text.strip()):
        last = lines[-1]
        while draw.textlength(last + "…", font=fnt) > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def nice_date(iso):
    d = datetime.datetime.fromisoformat(iso)
    return d.strftime("%-d %B %Y")


def feedback_png(fb, when):
    W, H = 1400, 600
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, W - 3, H - 3], 28, outline=GOLD, width=3, fill="#0b0b0b")
    d.text((60, 46), "LIVE eBAY FEEDBACK", font=font(30, True), fill=GOLD2)
    d.text((W - 60, 52), f"Updated {when}", font=font(26), fill=MUTED, anchor="ra")
    boxes = [
        (fb["positive_pct"], "positive feedback (last 12 months)"),
        (f'{fb["score"] // 100 * 100:,}+', "eBay feedback score"),
        (f'{fb["positive"]["12m"]:,}', f'positive ratings (12 months), {fb["negative_12m"]} negative'),
    ]
    dsr = fb.get("dsr", {})
    if dsr:
        avg = min(v["avg"] for v in dsr.values())
        boxes.append((f"{avg:.1f} / 5", "detailed seller ratings" + (" (all four)" if len(dsr) == 4 and all(v["avg"] == avg for v in dsr.values()) else " (lowest of four)")))
    gap, top = 20, 110
    bw = (W - 120 - gap * 3) // 4
    for i, (big, small) in enumerate(boxes):
        x = 60 + i * (bw + gap)
        d.rounded_rectangle([x, top, x + bw, top + 230], 20, outline=LINE, width=2, fill=PANEL)
        d.text((x + bw / 2, top + 40), big, font=font(64, True), fill=TEXT, anchor="ma")
        for j, ln in enumerate(wrap(d, small, font(24), bw - 40, 3)):
            d.text((x + bw / 2, top + 130 + j * 30), ln, font=font(24), fill=MUTED, anchor="ma")
    y = 380
    badges = []
    if fb.get("top_rated"): badges.append("eBay Top-rated seller")
    if fb.get("member_since"): badges.append("eBay member since 20" + fb["member_since"][-2:])
    badges.append("Registered business seller")
    d.text((60, y), "   •   ".join(badges), font=font(26, True), fill=GOLD2)
    y += 56
    for c in fb.get("recent_comments", [])[:2]:
        ln = wrap(d, f'“{c}”', font(27), W - 160, 1)[0]
        d.text((60, y), ln, font=font(27), fill=TEXT); y += 44
    d.text((W - 60, H - 40), "Tap to read all feedback on eBay  ›", font=font(24, True), fill=GOLD, anchor="rb")
    im.save(os.path.join(OUT, "feedback.png"), optimize=True)



def card_png(i, item):
    W, PH, H = 600, 600, 800
    im = Image.new("RGB", (W, H), PANEL); d = ImageDraw.Draw(im)
    if item:
        try:
            ph = ImageOps.fit(fetch_image(item["image"]), (W, PH), Image.LANCZOS)
            im.paste(ph, (0, 0))
        except Exception:
            d.rectangle([0, 0, W, PH], fill="#1a1a1a")
        for j, ln in enumerate(wrap(d, item["title"], font(30, True), W - 48, 3)):
            d.text((24, PH + 20 + j * 38), ln, font=font(30, True), fill=TEXT)
        price = item.get("price", "").replace(".00", "")
        d.text((24, H - 28), price, font=font(36, True), fill=GOLD2, anchor="ls")
        d.text((W - 24, H - 30), "View ›", font=font(26, True), fill=GOLD, anchor="rs")
    else:  # fewer live listings than slots
        d.text((W / 2, H / 2 - 20), "See all our", font=font(38, True), fill=TEXT, anchor="mm")
        d.text((W / 2, H / 2 + 30), "live listings ›", font=font(38, True), fill=GOLD2, anchor="mm")
    d.rectangle([0, 0, W - 1, H - 1], outline=LINE, width=2)
    im.save(os.path.join(OUT, f"card-{i}.jpg"), quality=85, optimize=True)
    # matching small header thumbnail
    th = im.crop((0, 0, W, PH)).resize((240, 240), Image.LANCZOS) if item else Image.new("RGB", (240, 240), PANEL)
    th.save(os.path.join(OUT, f"thumb-{i}.jpg"), quality=86)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = json.load(open(os.path.join(HERE, "data.json")))
    when = nice_date(data["fetched_at"])
    feedback_png(data["feedback"], when)
    items = data["listings"][:N_CARDS]
    for i in range(1, N_CARDS + 1):
        card_png(i, items[i - 1] if i <= len(items) else None)
    print("Images written to", OUT)


if __name__ == "__main__":
    main()

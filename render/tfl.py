#!/usr/bin/env python3
"""Render the TfL line-status board to public/tfl.png (preview) and
public/tfl.bin (packed 1-bit for the e-paper device).

Portable: font lookup covers macOS and Linux (GitHub Actions) so the same
script produces the same board locally and in CI.
"""
import os
import datetime
try:
    from zoneinfo import ZoneInfo
    LONDON = ZoneInfo("Europe/London")
except Exception:
    LONDON = None

import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 800, 480
MARGIN = 30
BLACK, WHITE = 0, 255
MODES = "tube,elizabeth-line,dlr,overground"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "public")

# font candidates: macOS first, then Linux (fonts-liberation / dejavu)
REG = ["/System/Library/Fonts/Helvetica.ttc",
       "/System/Library/Fonts/Supplemental/Arial.ttf",
       "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

def font(cands, size):
    for p in cands:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()

f_title = font(BOLD, 32)
f_date  = font(REG, 20)
f_line  = font(BOLD, 19)
f_stat  = font(REG, 17)
f_foot  = font(REG, 15)

def fetch_status():
    r = requests.get(f"https://api.tfl.gov.uk/Line/Mode/{MODES}/Status", timeout=20)
    r.raise_for_status()
    out = []
    for line in r.json():
        st = line.get("lineStatuses", [])
        desc = st[0]["statusSeverityDescription"] if st else "Unknown"
        out.append((line["name"], desc))
    return out

def pill(d, text, fnt, x_right, cy):
    tw = d.textlength(text, font=fnt)
    asc, desc = fnt.getmetrics(); th = asc + desc
    pad = 8
    x0 = x_right - tw - 2 * pad
    y0 = cy - th // 2 - 2; y1 = cy + th // 2 + 2
    d.rounded_rectangle([x0, y0, x_right, y1], radius=(y1 - y0) // 2, fill=BLACK)
    d.text((x0 + pad, cy - th // 2), text, font=fnt, fill=WHITE)

def render(lines, now):
    img = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.text((MARGIN, 20), "London Underground & Rail", font=f_title, fill=BLACK)
    stamp = now.strftime("as of %H:%M  ·  %a %d %b")
    tw = d.textlength(stamp, font=f_date)
    d.text((W - MARGIN - tw, 32), stamp, font=f_date, fill=BLACK)
    d.line([(MARGIN, 72), (W - MARGIN, 72)], fill=BLACK, width=3)

    per_col = (len(lines) + 1) // 2
    col_x = [MARGIN, W // 2 + 10]
    col_r = [W // 2 - 20, W - MARGIN]
    top, row_h = 92, 36
    for i, (name, status) in enumerate(lines):
        col, row = i // per_col, i % per_col
        x, xr = col_x[col], col_r[col]
        cy = top + row * row_h + row_h // 2
        d.text((x, cy - f_line.getmetrics()[0] // 2 - 2), name, font=f_line, fill=BLACK)
        if status == "Good Service":
            sw = d.textlength(status, font=f_stat)
            d.text((xr - sw, cy - f_stat.getmetrics()[0] // 2 - 1), status, font=f_stat, fill=BLACK)
        else:
            pill(d, status, f_stat, xr, cy)
    d.text((MARGIN, H - 26), "Live · TfL Unified API", font=f_foot, fill=BLACK)
    return img

def save(img):
    os.makedirs(OUT_DIR, exist_ok=True)
    img.save(os.path.join(OUT_DIR, "tfl.png"))
    # packed 1-bit, bit1=black (matches Adafruit drawBitmap w/ GxEPD_BLACK)
    raw = img.tobytes()                       # PIL: bit1=white
    data = bytes((~b) & 0xFF for b in raw)    # invert -> bit1=black
    with open(os.path.join(OUT_DIR, "tfl.bin"), "wb") as f:
        f.write(data)
    return len(data)

if __name__ == "__main__":
    now = datetime.datetime.now(LONDON) if LONDON else datetime.datetime.now()
    lines = fetch_status()
    n = save(render(lines, now))
    print(f"rendered {len(lines)} lines -> public/tfl.png + public/tfl.bin ({n} bytes)")

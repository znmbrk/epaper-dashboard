#!/usr/bin/env python3
"""Render a TfL line-status board to an 800x480 1-bit image for the e-paper.

Live data from the free TfL Unified API (no key required for line status).
Disruptions are shown as inverted (black) pills so they pop at a glance.
"""
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

W, H = 800, 480
MARGIN = 30
BLACK, WHITE = 0, 255

MODES = "tube,elizabeth-line,dlr,overground"

def font(cands, size):
    for p in cands:
        try: return ImageFont.truetype(p, size)
        except OSError: continue
    return ImageFont.load_default()

HELV      = ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"]
HELV_BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]
f_title = font(HELV_BOLD, 32)
f_date  = font(HELV, 20)
f_line  = font(HELV_BOLD, 19)
f_stat  = font(HELV, 17)
f_foot  = font(HELV, 15)

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
    """Right-aligned inverted pill (black bg, white text) for disruptions."""
    tw = d.textlength(text, font=fnt)
    asc, desc = fnt.getmetrics(); th = asc + desc
    pad = 8
    x1 = x_right; x0 = x_right - tw - 2 * pad
    y0 = cy - th // 2 - 2; y1 = cy + th // 2 + 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2, fill=BLACK)
    d.text((x0 + pad, cy - th // 2), text, font=fnt, fill=WHITE)

def render(lines, now):
    img = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    d.text((MARGIN, 20), "London Underground & Rail", font=f_title, fill=BLACK)
    stamp = now.strftime("as of %H:%M  ·  %a %d %b")
    tw = d.textlength(stamp, font=f_date)
    d.text((W - MARGIN - tw, 32), stamp, font=f_date, fill=BLACK)
    d.line([(MARGIN, 72), (W - MARGIN, 72)], fill=BLACK, width=3)

    # two columns
    per_col = (len(lines) + 1) // 2
    col_x   = [MARGIN, W // 2 + 10]
    col_r   = [W // 2 - 20, W - MARGIN]
    top, row_h = 92, 36

    for i, (name, status) in enumerate(lines):
        col = i // per_col
        row = i % per_col
        x = col_x[col]; xr = col_r[col]
        cy = top + row * row_h + row_h // 2
        d.text((x, cy - f_line.getmetrics()[0] // 2 - 2), name, font=f_line, fill=BLACK)
        if status == "Good Service":
            s = "Good Service"; sw = d.textlength(s, font=f_stat)
            d.text((xr - sw, cy - f_stat.getmetrics()[0] // 2 - 1), s, font=f_stat, fill=BLACK)
        else:
            pill(d, status, f_stat, xr, cy)

    d.text((MARGIN, H - 26), "Live · TfL Unified API", font=f_foot, fill=BLACK)
    return img

if __name__ == "__main__":
    lines = fetch_status()
    img = render(lines, datetime.datetime.now())
    out = "/Users/zainmobarik/projects/firebeetle-epaper/host/tfl_preview.png"
    img.save(out)
    print("wrote", out, "with", len(lines), "lines")

#!/usr/bin/env python3
"""Render a Strava-style run screen to an 800x480 1-bit image for the e-paper.

Prototype: uses a synthetic sample run so we can judge the layout with no
Strava auth. decode_polyline() is ready for real `map.summary_polyline` data.
"""
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 800, 480
MARGIN = 30
BLACK, WHITE = 0, 255

# ---------- fonts (macOS system fonts) ----------
def font(path_candidates, size):
    for p in path_candidates:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()

HELV = ["/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf"]
HELV_BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/System/Library/Fonts/Helvetica.ttc"]

f_title   = font(HELV_BOLD, 44)
f_date    = font(HELV, 24)
f_stat_lbl= font(HELV_BOLD, 20)
f_stat_big= font(HELV_BOLD, 60)
f_foot    = font(HELV, 18)

# ---------- Google encoded polyline decoder (for real Strava data) ----------
def decode_polyline(s):
    pts, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        for is_lat in (True, False):
            shift, result = 0, 0
            while True:
                b = ord(s[i]) - 63; i += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20: break
            d = ~(result >> 1) if (result & 1) else (result >> 1)
            if is_lat: lat += d
            else:      lng += d
        pts.append((lat * 1e-5, lng * 1e-5))
    return pts

# ---------- synthetic sample route (a wandering loop) ----------
def sample_route():
    base_lat, base_lng = 51.5074, -0.1278
    pts = []
    for k in range(240):
        t = k / 240 * 2 * math.pi
        r = 0.010 + 0.004 * math.sin(3 * t) + 0.002 * math.cos(5 * t)
        pts.append((base_lat + r * math.sin(t) * 0.7,
                    base_lng + r * math.cos(t)))
    return pts

# ---------- project lat/lng into a pixel box, preserving aspect ----------
def project(points, box):
    x0, y0, x1, y1 = box
    lats = [p[0] for p in points]; lngs = [p[1] for p in points]
    minlat, maxlat, minlng, maxlng = min(lats), max(lats), min(lngs), max(lngs)
    midlat = (minlat + maxlat) / 2
    # equirectangular with longitude compressed by cos(lat)
    def xy(lat, lng):
        return ((lng - minlng) * math.cos(math.radians(midlat)), (maxlat - lat))
    raw = [xy(la, ln) for la, ln in points]
    rx = [p[0] for p in raw]; ry = [p[1] for p in raw]
    spanx = max(rx) - min(rx) or 1e-9; spany = max(ry) - min(ry) or 1e-9
    bw, bh = x1 - x0, y1 - y0
    scale = min(bw / spanx, bh / spany) * 0.9
    offx = x0 + (bw - spanx * scale) / 2
    offy = y0 + (bh - spany * scale) / 2
    return [(offx + (px - min(rx)) * scale, offy + (py - min(ry)) * scale)
            for px, py in raw]

# ---------- formatting ----------
def fmt_dist(m):  return f"{m/1000:.2f} km"
def fmt_time(s):
    h, rem = divmod(int(s), 3600); mm, ss = divmod(rem, 60)
    return f"{h}:{mm:02d}:{ss:02d}" if h else f"{mm}:{ss:02d}"
def fmt_pace(m, s):
    if m == 0: return "-"
    p = s / (m / 1000); mm, ss = divmod(int(round(p)), 60)
    return f"{mm}:{ss:02d} /km"

def right(draw, text, fnt, x_right, y):
    w = draw.textlength(text, font=fnt); draw.text((x_right - w, y), text, font=fnt, fill=BLACK)

def render(run):
    img = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # title + date
    d.text((MARGIN, 22), run["name"], font=f_title, fill=BLACK)
    right(d, run["date"], f_date, W - MARGIN, 36)
    d.line([(MARGIN, 90), (W - MARGIN, 90)], fill=BLACK, width=3)

    # stats column (left)
    stats = [("DISTANCE", fmt_dist(run["distance_m"])),
             ("PACE",     fmt_pace(run["distance_m"], run["moving_time_s"])),
             ("MOVING TIME", fmt_time(run["moving_time_s"])),
             ("ELEVATION", f"{run['elev_m']:.0f} m")]
    y = 120
    for lbl, val in stats:
        d.text((MARGIN, y), lbl, font=f_stat_lbl, fill=BLACK)
        d.text((MARGIN, y + 22), val, font=f_stat_big, fill=BLACK)
        y += 92

    # route map (right)
    box = (410, 110, W - MARGIN, H - 50)
    d.rectangle(box, outline=BLACK, width=2)
    pts = project(run["route"], (box[0] + 12, box[1] + 12, box[2] - 12, box[3] - 12))
    d.line(pts, fill=BLACK, width=3, joint="curve")
    # start (filled) + end (ring)
    sx, sy = pts[0]; ex, ey = pts[-1]
    d.ellipse([sx-7, sy-7, sx+7, sy+7], fill=BLACK)
    d.ellipse([ex-7, ey-7, ex+7, ey+7], outline=BLACK, width=3)

    # footer
    right(d, "via Strava", f_foot, W - MARGIN, H - 34)
    return img

if __name__ == "__main__":
    run = {
        "name": "Morning Run",
        "date": "Sat 4 Oct 2026",
        "distance_m": 10420,
        "moving_time_s": 3248,     # 54:08
        "elev_m": 122,
        "route": sample_route(),   # swap for decode_polyline(summary_polyline)
    }
    img = render(run)
    img.save("/Users/zainmobarik/projects/firebeetle-epaper/host/run_preview.png")
    print("wrote run_preview.png")

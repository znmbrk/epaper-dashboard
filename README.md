# epaper-dashboard

A FireBeetle 2 ESP32-E driving a Waveshare 7.5" (800×480) e-paper display as a
swappable "frame". The device is a dumb renderer: it wakes on a timer, downloads
a pre-rendered 1-bit image, draws it, and deep-sleeps.

## How it works

```
render/  (Python)  →  public/tfl.bin  (48 KB, packed 1-bit)  →  device GET over WiFi
         ↑ GitHub Action re-renders on a schedule and commits the image
```

- **`render/tfl.py`** — fetches the free TfL Unified API (no key) and renders the
  London transport status board to `public/tfl.png` (preview) and
  `public/tfl.bin` (what the device fetches).
- **`public/tfl.bin`** — the live image, served at a stable raw URL.
- **`firmware/`** (PlatformIO) — ESP32 firmware. Wiring and flashing notes below.

## Image URL

```
https://raw.githubusercontent.com/znmbrk/epaper-dashboard/main/public/tfl.bin
```

## Local render

```
python3 -m venv host/.venv
host/.venv/bin/pip install -r requirements.txt
host/.venv/bin/python render/tfl.py
```

## Hardware

- Board: DFRobot FireBeetle 2 ESP32-E
- Display: Waveshare 7.5" V2, 800×480, B/W, UC8179 → GxEPD2 `GxEPD2_750_T7`
- Wiring (DESPI-C02 → FireBeetle): CS=13, DC=22, RST=21, BUSY=14, SCK=18, MOSI=23, GND, 3V3
- Flashing (macOS, WCH driver has no auto-reset): hold BOOT, tap RST, release BOOT,
  then upload; tap RST after to run.

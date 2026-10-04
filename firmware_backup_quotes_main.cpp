#include <Arduino.h>
#include <GxEPD2_BW.h>
#include <Fonts/FreeSerifItalic24pt7b.h>
#include <Fonts/FreeSans18pt7b.h>
#include "esp_sleep.h"

// --- Wiring: DESPI-C02 -> FireBeetle 2 ESP32-E ---
//   CS=13  DC=22  RST=21  BUSY=14   (SPI: SCK=18, MOSI=23 = default VSPI)
#define EPD_CS   13
#define EPD_DC   22
#define EPD_RST  21
#define EPD_BUSY 14

// Waveshare 7.5" V2, 800x480, B/W, UC8179
GxEPD2_BW<GxEPD2_750_T7, GxEPD2_750_T7::HEIGHT> display(
    GxEPD2_750_T7(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

// ---- Rotation interval ----
// TESTING: 25 seconds so we can watch it rotate.
// PRODUCTION: 3600 = one hour.
#define ROTATE_SECONDS 3600ULL

// ---- Your quotes (edit freely; keep authors short) ----
struct Quote { const char* text; const char* author; };
const Quote quotes[] = {
  {"The only way to do great work is to love what you do.", "Steve Jobs"},
  {"In the middle of difficulty lies opportunity.",          "Albert Einstein"},
  {"The unexamined life is not worth living.",               "Socrates"},
  {"The best way to predict the future is to invent it.",    "Alan Kay"},
  {"Simplicity is the ultimate sophistication.",             "Leonardo da Vinci"},
  {"Whether you think you can or you can't, you're right.",  "Henry Ford"},
  {"It always seems impossible until it's done.",            "Nelson Mandela"},
  {"The journey of a thousand miles begins with a single step.", "Lao Tzu"},
  {"We are what we repeatedly do; excellence is a habit.",   "Aristotle"},
  {"What we think, we become.",                              "Buddha"},
};
const int NUM_QUOTES = sizeof(quotes) / sizeof(quotes[0]);

// Survives deep sleep (kept in RTC memory). Set on cold boot only.
RTC_DATA_ATTR int quoteIndex = 0;

const int MARGIN = 60;  // side margin in px

// Split text into lines that fit within maxWidth using the current font.
int wrapText(const char* text, int maxWidth, String lines[], int maxLines) {
  String words = String(text);
  int nLines = 0;
  String current = "";
  int start = 0;
  while (start <= (int)words.length() && nLines < maxLines) {
    int sp = words.indexOf(' ', start);
    String word = (sp == -1) ? words.substring(start) : words.substring(start, sp);
    String trial = current.length() ? current + " " + word : word;
    int16_t bx, by; uint16_t bw, bh;
    display.getTextBounds(trial, 0, 0, &bx, &by, &bw, &bh);
    if ((int)bw > maxWidth && current.length() > 0) {
      lines[nLines++] = current;
      current = word;
    } else {
      current = trial;
    }
    if (sp == -1) break;
    start = sp + 1;
  }
  if (nLines < maxLines && current.length()) lines[nLines++] = current;
  return nLines;
}

void drawCentered(const String& s, int y) {
  int16_t bx, by; uint16_t bw, bh;
  display.getTextBounds(s, 0, 0, &bx, &by, &bw, &bh);
  int x = (display.width() - bw) / 2 - bx;
  display.setCursor(x, y);
  display.print(s);
}

void drawQuote(const Quote& q) {
  const int W = display.width();   // 800
  const int H = display.height();  // 480
  const int maxW = W - 2 * MARGIN;
  const int lineH = 52;            // spacing for 24pt serif

  display.setTextColor(GxEPD_BLACK);
  display.setFont(&FreeSerifItalic24pt7b);

  String lines[8];
  int n = wrapText(q.text, maxW, lines, 8);

  int blockH = n * lineH;
  int startY = (H - blockH) / 2 + 36;  // baseline nudge

  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);

    display.setFont(&FreeSerifItalic24pt7b);
    for (int i = 0; i < n; i++) {
      drawCentered(lines[i], startY + i * lineH);
    }

    // author, right-aligned under the quote
    display.setFont(&FreeSans18pt7b);
    String by = String("- ") + q.author;
    int16_t x1, y1; uint16_t aw, ah;
    display.getTextBounds(by, 0, 0, &x1, &y1, &aw, &ah);
    int ax = W - MARGIN - aw - x1;
    int ay = startY + n * lineH + 40;
    display.setCursor(ax, ay);
    display.print(by);
  } while (display.nextPage());
}

void setup() {
  Serial.begin(115200);
  delay(200);

  esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
  Serial.printf("\n=== wake (cause=%d) showing quote %d/%d ===\n",
                cause, quoteIndex + 1, NUM_QUOTES);
  Serial.printf("  \"%s\" - %s\n", quotes[quoteIndex].text, quotes[quoteIndex].author);

  display.init(115200);
  drawQuote(quotes[quoteIndex]);
  display.hibernate();   // panel low-power; image retained

  // advance index for next wake
  quoteIndex = (quoteIndex + 1) % NUM_QUOTES;

  // schedule next wake and sleep
  Serial.printf("sleeping %llus, next will be quote %d\n", ROTATE_SECONDS, quoteIndex + 1);
  Serial.flush();
  esp_sleep_enable_timer_wakeup(ROTATE_SECONDS * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {
  // never reached — deep sleep restarts setup() each cycle
}

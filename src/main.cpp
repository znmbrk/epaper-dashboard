#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <GxEPD2_BW.h>
#include "secrets.h"   // WIFI_SSID, WIFI_PASS (git-ignored)

// --- Wiring: DESPI-C02 -> FireBeetle 2 ESP32-E ---
//   CS=13  DC=22  RST=21  BUSY=14   (SPI: SCK=18, MOSI=23 = default VSPI)
#define EPD_CS   13
#define EPD_DC   22
#define EPD_RST  21
#define EPD_BUSY 14

// Quarter-height paged buffer (12 KB instead of 48 KB) to leave RAM for the
// 48 KB download buffer + TLS. GxEPD2 draws the full image in 4 bands.
GxEPD2_BW<GxEPD2_750_T7, GxEPD2_750_T7::HEIGHT / 4> display(
    GxEPD2_750_T7(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

// Pre-rendered 1-bit board, published hourly by the GitHub Action.
static const char* IMAGE_URL =
    "https://raw.githubusercontent.com/znmbrk/epaper-dashboard/main/public/tfl.bin";

#define IMG_W 800
#define IMG_H 480
#define IMG_BYTES (IMG_W * IMG_H / 8)   // 48000

#define SLEEP_OK_SEC   3600ULL          // 1 hour after a good update
#define SLEEP_FAIL_SEC 900ULL           // retry in 15 min on failure
#define WIFI_TIMEOUT_MS 20000UL

static uint8_t imgbuf[IMG_BYTES];

void deepSleep(uint64_t seconds) {
  Serial.printf("sleeping %llus\n", seconds);
  Serial.flush();
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  esp_sleep_enable_timer_wakeup(seconds * 1000000ULL);
  esp_deep_sleep_start();
}

bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > WIFI_TIMEOUT_MS) return false;
    delay(250);
  }
  return true;
}

// Download IMG_BYTES into imgbuf. Returns true only on a complete image.
bool fetchImage() {
  WiFiClientSecure client;
  client.setInsecure();               // public data; skip cert pinning
  HTTPClient http;
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  http.setTimeout(15000);
  if (!http.begin(client, IMAGE_URL)) return false;

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.printf("HTTP %d\n", code);
    http.end();
    return false;
  }

  WiFiClient* stream = http.getStreamPtr();
  size_t got = 0;
  uint32_t last = millis();
  while (http.connected() && got < IMG_BYTES) {
    size_t avail = stream->available();
    if (avail) {
      size_t want = IMG_BYTES - got;
      int r = stream->readBytes(imgbuf + got, avail < want ? avail : want);
      got += r;
      last = millis();
    } else if (millis() - last > 5000) {
      break;                          // stalled
    } else {
      delay(5);
    }
  }
  http.end();
  Serial.printf("received %u/%d bytes\n", (unsigned)got, IMG_BYTES);
  return got == IMG_BYTES;
}

void drawImageBuffer() {
  display.setRotation(0);
  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.drawBitmap(0, 0, imgbuf, IMG_W, IMG_H, GxEPD_BLACK);
  } while (display.nextPage());
  display.hibernate();
}

// Minimal status screen (used only on failure, for first-time setup).
void drawMessage(const char* line1, const char* line2) {
  display.setRotation(0);
  display.setFullWindow();
  display.setTextColor(GxEPD_BLACK);
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.setTextSize(3);
    display.setCursor(40, 210);
    display.print(line1);
    if (line2 && line2[0]) {
      display.setTextSize(2);
      display.setCursor(40, 260);
      display.print(line2);
    }
  } while (display.nextPage());
  display.hibernate();
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.printf("\n=== epaper frame wake (reset=%d) ===\n", esp_sleep_get_wakeup_cause());

  display.init(115200);

  if (!connectWiFi()) {
    Serial.println("WiFi connect failed");
    drawMessage("WiFi failed", WIFI_SSID);
    deepSleep(SLEEP_FAIL_SEC);
  }
  Serial.printf("WiFi ok  ip=%s  rssi=%d\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());

  if (fetchImage()) {
    Serial.println("fetch ok, drawing");
    drawImageBuffer();
    deepSleep(SLEEP_OK_SEC);
  } else {
    Serial.println("fetch failed");
    drawMessage("Fetch failed", "check image URL");
    deepSleep(SLEEP_FAIL_SEC);
  }
}

void loop() {
  // never reached — deep sleep restarts setup() each cycle
}

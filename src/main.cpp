#include <Arduino.h>
#include <GxEPD2_BW.h>
#include "tfl_image.h"

// --- Wiring: DESPI-C02 -> FireBeetle 2 ESP32-E ---
//   CS=13  DC=22  RST=21  BUSY=14   (SPI: SCK=18, MOSI=23 = default VSPI)
#define EPD_CS   13
#define EPD_DC   22
#define EPD_RST  21
#define EPD_BUSY 14

GxEPD2_BW<GxEPD2_750_T7, GxEPD2_750_T7::HEIGHT> display(
    GxEPD2_750_T7(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== TfL snapshot ===");

  display.init(115200);
  display.setRotation(0);
  display.setFullWindow();
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.drawBitmap(0, 0, tfl_image, 800, 480, GxEPD_BLACK);
  } while (display.nextPage());
  display.hibernate();

  Serial.println("snapshot drawn, hibernating");
}

void loop() {
  // static image — nothing to do
}

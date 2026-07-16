#pragma once

#include <Arduino.h>
#include <SPI.h>
#include <WiFiClient.h>

#include "config.h"

// Waveshare E6 nibble values (7.3" Spectra 6 class panels)
enum EpdColor : uint8_t {
  EPD_BLACK = 0x0,
  EPD_WHITE = 0x1,
  EPD_GREEN = 0x2,
  EPD_BLUE = 0x3,
  EPD_RED = 0x4,
  EPD_YELLOW = 0x5,
};

// Pi palette order: black, white, blue, green, red, yellow
static const uint8_t PI_INDEX_TO_EPD[6] = {
  EPD_BLACK,
  EPD_WHITE,
  EPD_BLUE,
  EPD_GREEN,
  EPD_RED,
  EPD_YELLOW,
};

void initPanel();
void send_command(uint8_t cmd);
void send_data(uint8_t data);
void send_data_buffer(const uint8_t* data, size_t length);
void waitUntilIdle();
void turnOnDisplay();
void sleepPanel();

bool streamPiFrameToPanel(WiFiClient& stream, uint32_t expectedBytes);

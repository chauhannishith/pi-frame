#pragma once

// ---------------------------------------------------------------------------
// Network — edit before flashing
// ---------------------------------------------------------------------------
static const char* const WIFI_SSID = "YOUR_WIFI_SSID";
static const char* const WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Pi Flask server (port 5000 inside Docker; use 5001 if mapped on Mac dev host)
static const char* const FRAME_URL = "http://192.168.1.100:5000/get_latest_frame.bin";

// ---------------------------------------------------------------------------
// Panel geometry (WVSH0103 — 7.3" E6, 800×480)
// ---------------------------------------------------------------------------
static const uint16_t FRAME_WIDTH = 800;
static const uint16_t FRAME_HEIGHT = 480;
static const uint32_t FRAME_BYTE_PAYLOAD = FRAME_WIDTH * FRAME_HEIGHT;  // Pi pack mode: byte

// ---------------------------------------------------------------------------
// Waveshare Universal e-Paper ESP32 Driver Board (SKU 15823) pin map
// ---------------------------------------------------------------------------
static const int PIN_EPD_CS = 5;
static const int PIN_EPD_RST = 16;
static const int PIN_EPD_DC = 17;
static const int PIN_EPD_BUSY = 4;
static const int PIN_WAKE_BUTTON = 12;

// SPI (VSPI default on ESP32-WROOM-32)
static const int PIN_SPI_SCK = 18;
static const int PIN_SPI_MOSI = 23;
static const int PIN_SPI_MISO = 19;

static const uint32_t SPI_CLOCK_HZ = 4000000;
static const uint32_t WIFI_CONNECT_TIMEOUT_MS = 30000;
static const uint32_t HTTP_TIMEOUT_MS = 120000;
static const uint64_t DEEP_SLEEP_US = 24ULL * 60ULL * 60ULL * 1000000ULL;  // 24 h

static const size_t HTTP_READ_CHUNK = 512;

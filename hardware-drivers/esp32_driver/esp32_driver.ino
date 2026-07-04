/**
 * pi-frame ESP32 firmware — Waveshare Universal e-Paper Driver Board (SKU 15823)
 *
 * Fetches the latest 800×480 6-color frame from the Pi Flask server and pushes
 * it to a 7.3" Spectra 6 (E6) panel over 4-wire SPI. After refresh, the ESP32
 * enters deep sleep until the 24-hour RTC timer fires or GPIO 12 is pressed.
 *
 * Target: ESP32-WROOM-32 @ 115200 baud
 * Arduino core: esp32 by Espressif (2.x+)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <esp_sleep.h>

#include "config.h"
#include "epd_panel.h"

// ---------------------------------------------------------------------------
// Serial helpers
// ---------------------------------------------------------------------------

static void logWakeupCause() {
  const esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();

  switch (cause) {
    case ESP_SLEEP_WAKEUP_TIMER:
      Serial.println("[BOOT] Wake cause: RTC timer (24-hour schedule)");
      break;
    case ESP_SLEEP_WAKEUP_EXT0:
      Serial.println("[BOOT] Wake cause: GPIO 12 manual button (EXT0)");
      break;
    case ESP_SLEEP_WAKEUP_UNDEFINED:
    default:
      Serial.println("[BOOT] Wake cause: power-on / reset / first boot");
      break;
  }
}

static bool connectWiFi() {
  Serial.printf("[WIFI] Connecting to \"%s\" ", WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t deadline = millis() + WIFI_CONNECT_TIMEOUT_MS;
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() > deadline) {
      Serial.println();
      Serial.println("[WIFI] ERROR: connection timeout");
      return false;
    }
    delay(250);
    Serial.print('.');
  }

  Serial.println();
  Serial.print("[WIFI] Connected — IP: ");
  Serial.println(WiFi.localIP());
  Serial.printf("[WIFI] RSSI: %d dBm\n", WiFi.RSSI());
  return true;
}

static bool fetchAndDisplayFrame() {
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.setReuse(false);

  Serial.printf("[HTTP] GET %s\n", FRAME_URL);

  if (!http.begin(FRAME_URL)) {
    Serial.println("[HTTP] ERROR: begin() failed — check URL scheme/host");
    return false;
  }

  const int httpCode = http.GET();
  Serial.printf("[HTTP] Response code: %d\n", httpCode);

  if (httpCode != HTTP_CODE_OK) {
    Serial.printf("[HTTP] ERROR: unexpected status %d\n", httpCode);
    http.end();
    return false;
  }

  const int contentLength = http.getSize();
  Serial.printf("[HTTP] Content-Length: %d bytes\n", contentLength);

  if (contentLength > 0 && static_cast<uint32_t>(contentLength) != FRAME_BYTE_PAYLOAD) {
    Serial.printf(
      "[HTTP] WARN: payload size mismatch (expected %u). Proceeding with streamed count.\n",
      FRAME_BYTE_PAYLOAD
    );
  }

  WiFiClient* stream = http.getStreamPtr();
  if (stream == nullptr) {
    Serial.println("[HTTP] ERROR: null response stream");
    http.end();
    return false;
  }

  const uint32_t expected = (contentLength > 0) ? static_cast<uint32_t>(contentLength) : FRAME_BYTE_PAYLOAD;
  const bool ok = streamPiFrameToPanel(*stream, expected);

  http.end();
  return ok;
}

static void enterDeepSleep() {
  Serial.println("[SLEEP] Configuring wake sources");

  pinMode(PIN_WAKE_BUTTON, INPUT_PULLUP);
  esp_sleep_enable_ext0_wakeup(static_cast<gpio_num_t>(PIN_WAKE_BUTTON), 0);

  esp_sleep_enable_timer_wakeup(DEEP_SLEEP_US);

  Serial.printf("[SLEEP] RTC timer armed for %llu us (24 h)\n", DEEP_SLEEP_US);
  Serial.println("[SLEEP] EXT0 wake armed on GPIO 12 (active LOW)");
  Serial.println("[SLEEP] Entering ESP32 deep sleep — see you on next wake");
  Serial.flush();

  esp_deep_sleep_start();
}

// ---------------------------------------------------------------------------
// Arduino entry points
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println();
  Serial.println("========================================");
  Serial.println(" pi-frame ESP32 e-Paper client");
  Serial.println(" Board: Waveshare SKU 15823");
  Serial.println(" Panel: 7.3\" E6 800x480");
  Serial.println("========================================");

  logWakeupCause();

  // Future manual wake button — pull-up now, EXT0 armed before deep sleep
  pinMode(PIN_WAKE_BUTTON, INPUT_PULLUP);
  Serial.println("[GPIO] Wake button on GPIO 12 (INPUT_PULLUP)");

  if (!connectWiFi()) {
    Serial.println("[FATAL] Wi-Fi failed — sleeping 5 minutes before retry");
    esp_sleep_enable_timer_wakeup(5ULL * 60ULL * 1000000ULL);
    esp_sleep_enable_ext0_wakeup(static_cast<gpio_num_t>(PIN_WAKE_BUTTON), 0);
    esp_deep_sleep_start();
  }

  initPanel();

  if (!fetchAndDisplayFrame()) {
    Serial.println("[FATAL] Frame fetch/display failed");
    sleepPanel();
    enterDeepSleep();
  }

  sleepPanel();
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);

  enterDeepSleep();
}

void loop() {
  // setup() ends in deep sleep; loop is unreachable in normal operation
}

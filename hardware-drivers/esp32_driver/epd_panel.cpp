#include "epd_panel.h"

namespace {

SPIClass epdSpi(VSPI);

class NibbleStreamer {
 public:
  void reset() {
    haveHighNibble_ = false;
    highNibble_ = EPD_WHITE;
  }

  void pushPiIndex(uint8_t piIndex) {
    const uint8_t epd = (piIndex < 6) ? PI_INDEX_TO_EPD[piIndex] : EPD_WHITE;
    if (!haveHighNibble_) {
      highNibble_ = epd;
      haveHighNibble_ = true;
      return;
    }
    send_data(static_cast<uint8_t>((highNibble_ << 4) | (epd & 0x0F)));
    haveHighNibble_ = false;
  }

  void flushWithWhitePad() {
    if (haveHighNibble_) {
      send_data(static_cast<uint8_t>((highNibble_ << 4) | EPD_WHITE));
      haveHighNibble_ = false;
    }
  }

 private:
  bool haveHighNibble_ = false;
  uint8_t highNibble_ = EPD_WHITE;
};

void hardwareReset() {
  digitalWrite(PIN_EPD_RST, HIGH);
  delay(20);
  digitalWrite(PIN_EPD_RST, LOW);
  delay(2);
  digitalWrite(PIN_EPD_RST, HIGH);
  delay(20);
}

}  // namespace

void send_command(uint8_t cmd) {
  digitalWrite(PIN_EPD_CS, LOW);
  digitalWrite(PIN_EPD_DC, LOW);
  epdSpi.transfer(cmd);
  digitalWrite(PIN_EPD_CS, HIGH);
}

void send_data(uint8_t data) {
  digitalWrite(PIN_EPD_CS, LOW);
  digitalWrite(PIN_EPD_DC, HIGH);
  epdSpi.transfer(data);
  digitalWrite(PIN_EPD_CS, HIGH);
}

void send_data_buffer(const uint8_t* data, size_t length) {
  if (length == 0) {
    return;
  }
  digitalWrite(PIN_EPD_CS, LOW);
  digitalWrite(PIN_EPD_DC, HIGH);
  epdSpi.writeBytes(data, length);
  digitalWrite(PIN_EPD_CS, HIGH);
}

void waitUntilIdle() {
  // Waveshare 7.3" E6: BUSY low = updating, high = idle
  const uint32_t deadline = millis() + 120000;
  while (digitalRead(PIN_EPD_BUSY) == LOW) {
    if (millis() > deadline) {
      Serial.println("[EPD] ERROR: waitUntilIdle timeout");
      return;
    }
    delay(5);
  }
}

void initPanel() {
  pinMode(PIN_EPD_CS, OUTPUT);
  pinMode(PIN_EPD_DC, OUTPUT);
  pinMode(PIN_EPD_RST, OUTPUT);
  pinMode(PIN_EPD_BUSY, INPUT);

  digitalWrite(PIN_EPD_CS, HIGH);
  digitalWrite(PIN_EPD_DC, LOW);
  digitalWrite(PIN_EPD_RST, HIGH);

  epdSpi.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_EPD_CS);
  epdSpi.setFrequency(SPI_CLOCK_HZ);
  epdSpi.setDataMode(SPI_MODE0);
  epdSpi.setBitOrder(MSBFIRST);

  Serial.println("[EPD] Hardware reset");
  hardwareReset();
  waitUntilIdle();
  delay(30);

  // Init sequence from Waveshare epd7in3e (7.3" E6 / Spectra 6, 800×480)
  Serial.println("[EPD] Sending register init table");

  send_command(0xAA);
  send_data(0x49);
  send_data(0x55);
  send_data(0x20);
  send_data(0x08);
  send_data(0x09);
  send_data(0x18);

  send_command(0x01);
  send_data(0x3F);

  send_command(0x00);
  send_data(0x5F);
  send_data(0x69);

  send_command(0x03);
  send_data(0x00);
  send_data(0x54);
  send_data(0x00);
  send_data(0x44);

  send_command(0x05);
  send_data(0x40);
  send_data(0x1F);
  send_data(0x1F);
  send_data(0x2C);

  send_command(0x06);
  send_data(0x6F);
  send_data(0x1F);
  send_data(0x17);
  send_data(0x49);

  send_command(0x08);
  send_data(0x6F);
  send_data(0x1F);
  send_data(0x1F);
  send_data(0x22);

  send_command(0x30);
  send_data(0x03);

  send_command(0x50);
  send_data(0x3F);

  send_command(0x60);
  send_data(0x02);
  send_data(0x00);

  send_command(0x61);
  send_data(0x03);
  send_data(0x20);
  send_data(0x01);
  send_data(0xE0);

  send_command(0x84);
  send_data(0x01);

  send_command(0xE3);
  send_data(0x2F);

  send_command(0x04);  // POWER_ON
  waitUntilIdle();

  Serial.println("[EPD] Panel init complete");
}

void turnOnDisplay() {
  Serial.println("[EPD] POWER_ON");
  send_command(0x04);
  waitUntilIdle();

  Serial.println("[EPD] DISPLAY_REFRESH (~25 s)");
  send_command(0x12);
  send_data(0x00);
  waitUntilIdle();

  Serial.println("[EPD] POWER_OFF");
  send_command(0x02);
  send_data(0x00);
  waitUntilIdle();
}

void sleepPanel() {
  Serial.println("[EPD] DEEP_SLEEP (panel hibernate)");
  send_command(0x07);
  send_data(0xA5);
  delay(200);
  digitalWrite(PIN_EPD_RST, LOW);
}

bool streamPiFrameToPanel(Stream& stream, uint32_t expectedBytes) {
  if (expectedBytes != FRAME_BYTE_PAYLOAD) {
    Serial.printf(
      "[EPD] ERROR: expected %u byte indices, server sent %u\n",
      FRAME_BYTE_PAYLOAD,
      expectedBytes
    );
    return false;
  }

  NibbleStreamer packer;
  packer.reset();

  send_command(0x10);  // DATA_START_TRANSMISSION
  Serial.println("[EPD] Streaming VRAM (Pi byte indices -> E6 nibbles)");

  uint8_t chunk[HTTP_READ_CHUNK];
  uint32_t received = 0;
  uint32_t packedBytes = 0;

  while (received < expectedBytes) {
    const int available = stream.available();
    if (available == 0) {
      if (!stream.connected()) {
        Serial.println("[EPD] ERROR: HTTP stream closed early");
        return false;
      }
      delay(1);
      continue;
    }

    const int toRead = static_cast<int>(min(static_cast<uint32_t>(sizeof(chunk)), expectedBytes - received));
    const int n = stream.readBytes(chunk, min(toRead, available));
    if (n <= 0) {
      delay(1);
      continue;
    }

    for (int i = 0; i < n; ++i) {
      packer.pushPiIndex(chunk[i]);
      ++received;
    }

    packedBytes = (received + 1) / 2;

    if ((received % 16000) == 0 || received == expectedBytes) {
      Serial.printf("[EPD] Progress: %u / %u indices (%u packed bytes)\n", received, expectedBytes, packedBytes);
    }
  }

  packer.flushWithWhitePad();

  const uint32_t expectedPacked = (FRAME_WIDTH * FRAME_HEIGHT) / 2;
  if (packedBytes != expectedPacked) {
    Serial.printf("[EPD] WARN: packed byte count %u (expected %u)\n", packedBytes, expectedPacked);
  }

  Serial.println("[EPD] VRAM upload complete");
  turnOnDisplay();
  return true;
}

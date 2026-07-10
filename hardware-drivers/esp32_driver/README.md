# ESP32 Driver Firmware (SKU 15823)

Production firmware for the **Waveshare Universal e-Paper ESP32 Driver Board** (SKU **15823**), driving the **7.3" 6-color E6 panel** (800×480, WVSH0103) and fetching processed frames from the Pi Flask server.

## Hardware

| Signal | ESP32 GPIO |
|--------|------------|
| CS     | 5          |
| RST    | 16         |
| DC     | 17         |
| BUSY   | 4          |
| Wake button (future) | 12 |
| SPI SCK | 18        |
| SPI MOSI | 23       |
| SPI MISO | 19       |

> GPIO 12 is a boot strapping pin on ESP32. Avoid holding it LOW during reset.

## Pi server payload

The firmware expects **`BINARY_PACK_MODE=byte`** from `pi-server` (default): one palette index per pixel, 384000 bytes total.

Indices are remapped on-the-fly to Waveshare E6 4-bit nibbles (2 pixels/byte) and streamed over SPI without holding the full frame in RAM.

| Pi index | Color  | EPD nibble |
|----------|--------|------------|
| 0        | Black  | 0          |
| 1        | White  | 1          |
| 2        | Blue   | 3          |
| 3        | Green  | 2          |
| 4        | Red    | 4          |
| 5        | Yellow | 5          |

Endpoint: `GET /get_latest_frame.bin`

## Configuration

Edit `config.h` before flashing:

- `WIFI_SSID` / `WIFI_PASSWORD`
- `FRAME_URL` — Pi IP and port (5000 in Docker, 5001 on Mac dev host)
- `DAILY_WAKE_HHMM` — daily fetch time as HHMM (default `300` = 03:00), match Pi `DAILY_CHANGE_TIME`
- `PERIODIC_WAKE_SEC` — also wake every 12 hours (default `43200`)
- `TZ_OFFSET_SEC` — local timezone offset from UTC (default `19800` = IST, match Pi `TZ`)

## Build (Arduino IDE)

1. Install **esp32** board support (Espressif, v2.x+)
2. Board: **ESP32 Dev Module**
3. Open `esp32_driver.ino`
4. Upload at **115200** baud

## Build (arduino-cli)

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 hardware-drivers/esp32_driver
arduino-cli upload  --fqbn esp32:esp32:esp32 -p /dev/cu.usbserial-* hardware-drivers/esp32_driver
```

## Runtime flow

1. Log `esp_sleep_get_wakeup_cause()` (timer vs GPIO 12 vs cold boot)
2. Connect Wi-Fi (30 s timeout)
3. NTP time sync (`pool.ntp.org`, `TZ_OFFSET_SEC`)
4. `initPanel()` — Waveshare epd7in3e register sequence
5. HTTP GET frame → chunk read → SPI VRAM stream (`0x10`)
6. Full refresh (~25 s) via `0x12`
7. Panel deep sleep (`0x07 0xA5`)
8. ESP32 deep sleep — wake on **GPIO 12 LOW**, **daily `DAILY_WAKE_HHMM`**, or **every 12 h** (whichever is sooner)

## Serial monitor

```bash
screen /dev/cu.usbserial-* 115200
```

Look for state lines prefixed with `[BOOT]`, `[WIFI]`, `[HTTP]`, `[EPD]`, `[SLEEP]`.

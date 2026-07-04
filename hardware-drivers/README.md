# Hardware Drivers

Low-level display interface for:

| Component | SKU |
|---|---|
| Display panel | **WVSH0103** — 7.3-inch 6-Color E-Paper, 800×480 px |
| Driver board | **061-15823** — SPI driver board *(integration pending)* |

This folder is for bare-metal Pi development — SPI/GPIO wiring, pin configuration, and raw display test scripts. It runs **outside** the Docker container in `pi-server/`.

## Pin connections (BCM numbering)

Typical wiring for an SPI e-ink HAT or breakout board:

| Display signal | Pi GPIO (BCM) | Pi physical pin |
|---|---|---|
| VCC | 3.3 V | 1 or 17 |
| GND | GND | 6, 9, 14, 20, 25, 30, 34, or 39 |
| DIN (MOSI) | GPIO 10 | 19 |
| CLK (SCLK) | GPIO 11 | 23 |
| CS | GPIO 8 (CE0) | 24 |
| DC | GPIO 25 | 22 |
| RST | GPIO 17 | 11 |
| BUSY | GPIO 24 | 18 |

> Pin assignments vary by manufacturer. Confirm against your panel's datasheet before powering on.

## Enable SPI on the Pi

```bash
sudo raspi-config
# Interface Options → SPI → Enable
```

Reboot, then verify:

```bash
ls /dev/spidev*
# Expected: /dev/spidev0.0  /dev/spidev0.1
```

## Install dependencies (on the Pi host, not in Docker)

```bash
sudo apt install python3-spidev python3-rpi.gpio
```

## Run the test script

```bash
python3 driver_test.py
```

This skeleton initializes SPI and GPIO, sends placeholder commands, and prints status. Replace the TODO sections with your panel-specific driver logic.

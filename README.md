# pi-frame

Self-contained workspace for a **7.3-inch 6-color e-ink photo frame** on a **Raspberry Pi 4 Model B**.

## Target hardware

| Component | SKU | Spec |
|---|---|---|
| **Display panel** | **WVSH0103** | 7.3-inch 6-Color E-Paper, 800×480 px, low power (Spectra 6) |
| **Driver board** | **061-15823** | SPI driver board for the panel *(driver integration pending)* |

The image-processing pipeline in `pi-server/` is configured for **800×480** and a **6-color** palette (black, white, green, blue, red, yellow). The hardware driver in `hardware-drivers/` still needs to be written against the **061-15823** board spec.

## Implementation status

| Layer | Status |
|---|---|
| Image resize / crop to 800×480 | Done |
| 6-color palette quantization (CIE L\*a\*b\*) | Done |
| Error diffusion dithering (Floyd-Steinberg, Atkinson) | Done |
| Raw binary frame export | Done |
| Daily processing + HTTP delivery | Done |
| Unit tests (processing pipeline) | Done |
| Palette calibrated to WVSH0103 ink colors | Not yet — uses ideal RGB swatches |
| Binary byte layout matched to 061-15823 driver | Not yet — needs driver datasheet |
| SPI display driver (`hardware-drivers/`) | Pending |

The repository splits into two concerns:

| Directory | Purpose |
|---|---|
| [`pi-server/`](pi-server/) | Dockerized image-processing service — daily dithering pipeline + HTTP frame delivery |
| [`hardware-drivers/`](hardware-drivers/) | Bare-metal SPI/GPIO drivers, pinout docs, and low-level display test scripts |

## How the pieces fit together

```
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi 4 (Raspberry Pi OS Lite, 64-bit)          │
│                                                         │
│  ┌─────────────────────┐   ┌──────────────────────────┐ │
│  │  pi-server/ (Docker)│   │  hardware-drivers/       │ │
│  │                     │   │  (runs on Pi host)       │ │
│  │  Daily image        │   │                          │ │
│  │  processing ────────┼───┼─► SPI/GPIO ──► WVSH0103   │ │
│  │  Flask :5000        │   │  display panel           │ │
│  └─────────────────────┘   └──────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         ▲
         │  GET /get_latest_frame.bin
         │  (frame firmware or display client)
```

1. **`pi-server`** processes travel/environment photos on a 24-hour schedule, converts them into a binary frame buffer, and serves it at `/get_latest_frame.bin`.
2. **`hardware-drivers`** handles the physical layer — wiring the panel to the Pi's SPI bus and sending raw commands to the display controller.

## Repository layout

```
pi-frame/
├── README.md                  ← you are here
├── pi-server/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── app/
│       ├── app.py             Flask server + daily processing thread
│       └── processing/        Resize, dither, binary export pipeline
└── hardware-drivers/
    ├── README.md              Pinout and SPI setup guide
    └── driver_test.py         SPI/GPIO test skeleton
```

## Prerequisites

- Raspberry Pi 4 Model B with Raspberry Pi OS Lite (64-bit)
- [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) on the Pi
- SPI enabled for hardware driver work (`sudo raspi-config` → Interface Options → SPI)

## Run the Docker stack

All server commands run from the `pi-server/` directory:

```bash
cd pi-server
docker compose up --build -d
```

This will:

- Build a Python 3.11 slim image with Pillow, numpy, and Flask
- Start the container on port **5000**
- Mount `./app` into the container at `/app`
- Set timezone to **Asia/Kolkata**
- Restart automatically unless stopped

### Common commands

```bash
cd pi-server

docker compose logs -f          # tail logs
docker compose restart          # pick up app.py changes
docker compose down             # stop
docker compose up --build -d    # rebuild after dependency changes
```

### Fetch the latest frame

```bash
curl -O http://<pi-ip-address>:5000/get_latest_frame.bin
```

Returns `application/octet-stream` from `/app/latest_frame.bin`. Responds with **404** until the processing pipeline generates a frame.

## Configuration

Environment variables can be set in `pi-server/docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `LATEST_FRAME_PATH` | `/app/latest_frame.bin` | Output binary served by the API |
| `SOURCE_IMAGES_DIR` | `/app/source_images` | Directory for input photos |
| `FRAME_WIDTH` | `800` | Target frame width (pixels) |
| `FRAME_HEIGHT` | `480` | Target frame height (pixels) |
| `PROCESSING_INTERVAL_SECONDS` | `86400` | Seconds between processing cycles |
| `DITHER_METHOD` | `floyd_steinberg` | `floyd_steinberg`, `atkinson`, or `nearest` |
| `BINARY_PACK_MODE` | `byte` | `byte` (1 index/byte) or `packed` (3-bit) |
| `FLASK_HOST` | `0.0.0.0` | Flask bind address |
| `FLASK_PORT` | `5000` | Flask listen port |

## Image processing pipeline

Implemented in `pi-server/app/processing/`:

1. Load source image from `SOURCE_IMAGES_DIR`
2. Resize / crop to **800×480** (`resize.py` — cover, contain, or stretch)
3. Quantize to 6 palette colors with CIE L\*a\*b\* matching (`color.py`, `dither.py`)
4. Pack indices into a raw binary buffer (`binary.py`)
5. Write to `LATEST_FRAME_PATH` for the Flask endpoint to serve

Drop a photo into `pi-server/app/source_images/` on the Pi, restart the container, and the background thread will process it on startup (then every 24 h).

To process a single image manually:

```python
from processing import process_image_to_binary

process_image_to_binary("source_images/photo.jpg", "latest_frame.bin")
```

Palette swatches live in `pi-server/app/palette.py`. Tune `EINK_PALETTE_RGB` once you can photograph the actual WVSH0103 ink colors.

## Hardware drivers

Target panel: **WVSH0103** (800×480, 6-color) via driver board **061-15823**.

See [`hardware-drivers/README.md`](hardware-drivers/README.md) for:

- BCM pinout table (MOSI, SCLK, CS, DC, RST, BUSY)
- Enabling SPI on the Pi
- Installing `python3-spidev` and `python3-rpi.gpio`
- Running the test skeleton:

```bash
cd hardware-drivers
python3 driver_test.py
```

The test script initializes SPI/GPIO, provides command/data helpers, and has TODO markers for your panel-specific init sequence.

## Remote development

Edit code on a Mac (or any machine) over SSH with Cursor. Changes under `pi-server/app/` take effect after `docker compose restart`. Hardware driver scripts run directly on the Pi host.

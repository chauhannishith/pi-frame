# pi-frame

Self-contained workspace for a **7.3-inch 6-color e-ink photo frame** on a **Raspberry Pi 4 Model B**.

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
│  │  processing ────────┼───┼─► SPI/GPIO ──► E-ink     │ │
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
│       └── app.py             Flask server + daily processing thread
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
| `FLASK_HOST` | `0.0.0.0` | Flask bind address |
| `FLASK_PORT` | `5000` | Flask listen port |

## Adding image processing logic

Edit `process_images()` in `pi-server/app/app.py`. The intended workflow:

1. Load source images from `SOURCE_IMAGES_DIR`
2. Resize or crop to `FRAME_WIDTH` × `FRAME_HEIGHT`
3. Apply 6-color dithering (Atkinson, Floyd-Steinberg, etc.)
4. Pack pixels into a binary frame buffer
5. Write the result to `LATEST_FRAME_PATH`

Place input photos in `pi-server/app/source_images/` on the host.

## Hardware drivers

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

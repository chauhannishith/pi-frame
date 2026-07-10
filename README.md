# pi-frame

Turn a **7.3-inch 6-color e-ink panel** into a Wi-Fi photo frame. A Raspberry Pi runs a small web app that dithers your photos to the panel palette; an **ESP32 driver board** fetches the latest frame over HTTP and refreshes the display.

**You do not need Google Photos.** Upload JPG/PNG files through the web gallery on your LAN and push them to the frame. Google import is optional.

## What you get

| Feature | Description |
|---|---|
| **Web gallery** | Upload, browse, and delete photos from any browser on your network |
| **Preview before push** | Generate a dithered preview in the browser without updating the physical frame |
| **Push to frame** | Write `latest_frame.bin` for the ESP32 to fetch |
| **CHANGE** | Advance to the next library photo and push it |
| **Dither methods** | Floyd-Steinberg (default) or Atkinson |
| **Orientation** | Landscape (800×480) or portrait (processed tall, rotated for the panel) |
| **Quick actions** | Toggle dither or orientation from the gallery sidebar (desktop) or Settings (mobile) |
| **Face-aware crop** | OpenCV focal crop for landscape and portrait sources |
| **Google Photos** | Optional OAuth import via the Photos Picker API |

## Target hardware

| Component | Notes |
|---|---|
| **Panel** | Waveshare 7.3" 6-color E6 (800×480, WVSH0103 / Spectra 6) |
| **Driver board** | Waveshare Universal e-Paper ESP32 Driver Board (SKU **15823**) |
| **Pi** | Raspberry Pi 4 (or any host that can run Docker and reach the ESP32 over Wi-Fi) |

The processing pipeline targets **800×480** and a **6-color** palette (black, white, green, blue, red, yellow). See [`hardware-drivers/esp32_driver/README.md`](hardware-drivers/esp32_driver/README.md) for firmware setup.

## Quick start (local photos only)

This is the recommended path. No Google account or API keys required.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A machine on your LAN (Mac for development, Raspberry Pi for production)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USER/pi-frame.git
cd pi-frame/pi-server
cp .env.example .env
```

Edit `.env` and set at least:

```bash
FLASK_SECRET_KEY=replace-with-a-long-random-string
```

Leave `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` empty. The gallery works without them.

### 2. Create runtime directories

```bash
mkdir -p app/source_images app/data
```

Photos and settings are stored here on the host (the container mounts `./app`).

### 3. Start the server

```bash
docker compose up --build -d
```

On macOS, Docker maps host port **5001** → container **5000** (avoids conflict with AirPlay Receiver). On a Pi you can change the mapping in `docker-compose.yml` if you prefer port 5000 on the host.

Open the gallery:

| Environment | URL |
|---|---|
| Mac / dev | http://localhost:5001/gallery |
| Pi on LAN | http://\<pi-ip\>:5001/gallery |

### 4. Add photos and update the frame

1. **Upload** — use the **+ Add photos** tile or the upload form when the library is empty (JPG/PNG).
2. **Open a photo** — click a thumbnail or **Preview**.
3. **Generate preview** — pick dither method and orientation, then **Generate preview** to see the dithered result (`preview.png`).
4. **Push to frame** — **Push to frame** writes `latest_frame.bin` on the Pi.
5. **Refresh the e-ink panel** — press the **wake button** on the ESP32 driver board (GPIO 12). The ESP32 also wakes on a 24-hour timer configured in firmware.

**CHANGE** (header button) skips to the next photo in library rotation and pushes it to the frame.

### 5. Quick actions (sidebar / mobile Settings)

After you have previewed or pushed at least one photo, you can:

- **Switch dither** (Floyd-Steinberg ↔ Atkinson)
- **Switch orientation** (Landscape ↔ Portrait)

These reprocess the **original library file** (not the previous dithered output) and update `latest_frame.bin`. Press the wake button to refresh the display.

### Useful commands

From `pi-server/`:

```bash
make up          # start container
make logs-f      # follow logs
make restart     # restart after code changes
make test        # run pytest on the host
make fetch-frame # download latest_frame.bin (HOST= IP PORT=5001)
```

Or use `docker compose` directly — see the [Makefile](pi-server/Makefile).

## How the pieces fit together

```
  Browser (phone / laptop on LAN)
       │
       │  upload, preview, push
       ▼
  ┌──────────────────────────────────────┐
  │  pi-server (Docker, Flask)           │
  │  • Gallery + settings web UI         │
  │  • Resize, dither, pack frame binary │
  │  • source_images/  → originals       │
  │  • latest_frame.bin → ESP32 payload  │
  │  • preview.png     → browser preview │
  └──────────────┬───────────────────────┘
                 │  GET /get_latest_frame.bin
                 ▼
  ┌──────────────────────────────────────┐
  │  ESP32 driver (hardware-drivers/)    │
  │  Wi-Fi → fetch binary → SPI → panel  │
  │  Wake: GPIO 12, daily HHMM, or every 12 h │
  └──────────────────────────────────────┘
```

**Daily rotation:** the Pi advances to the next gallery photo at a fixed local time (`DAILY_CHANGE_TIME`, default **03:00**). The ESP32 fetches the latest frame on the same daily time (set in firmware `config.h`), **every 12 hours**, or when you press the **wake button**. Manual preview/push/CHANGE still work anytime.

## Web UI

| Page | Path | Purpose |
|---|---|---|
| Gallery | `/gallery` | Library grid, upload, CHANGE, sidebar status and quick actions |
| Image detail | `/gallery/view/<filename>` | Original, dithered preview, dither/orientation, preview & push |
| Settings | `/settings` | Default dither method; quick actions on mobile |
| Google Photos | `/google` | Optional import (requires OAuth credentials) |

Legacy `/upload` and `/preview` redirect to the gallery.

## HTTP API

| Endpoint | Description |
|---|---|
| `GET /get_latest_frame.bin` | Raw frame buffer for the ESP32 (404 until first push) |
| `GET /preview.png` | Dithered PNG for the browser (404 until first preview/push) |
| `GET /gallery/thumb/<filename>` | JPEG thumbnail |
| `GET /gallery/file/<filename>` | Original library file |

Frame binary format: one palette index per byte (`BINARY_PACK_MODE=byte`, default), 800×480 = 384000 bytes. The ESP32 firmware remaps indices to the Waveshare E6 wire format.

## Google Photos (optional)

Skip this section if you only use local uploads.

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Photos Picker API**.
3. Configure the OAuth consent screen and add yourself as a test user.
4. Create an OAuth **Web application** client.
5. Set the redirect URI to match how you open the app, e.g. `http://localhost:5001/google/callback` or `http://192.168.x.x.sslip.io:5001/google/callback` (Google rejects bare IP redirect URIs).
6. Copy client ID and secret into `pi-server/.env`.

See comments in [`pi-server/.env.example`](pi-server/.env.example) for details.

## Configuration

Environment variables are loaded from `pi-server/.env` (see `docker-compose.yml`). Common options:

| Variable | Default | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | *(required)* | Session signing for OAuth and uploads |
| `LATEST_FRAME_PATH` | `/app/latest_frame.bin` | Frame binary served to the ESP32 |
| `PREVIEW_PATH` | `/app/preview.png` | Browser preview image |
| `SOURCE_IMAGES_DIR` | `/app/source_images` | Photo library |
| `DATA_DIR` | `/app/data` | Settings, rotation state, Google token |
| `FRAME_WIDTH` / `FRAME_HEIGHT` | `800` / `480` | Panel dimensions |
| `DAILY_CHANGE_TIME` | `0300` | Daily gallery rotation at local HHMM (uses `TZ`) |
| `TZ` | `UTC` | Timezone for daily rotation (set in `docker-compose.yml` on Pi) |
| `DITHER_METHOD` | `floyd_steinberg` | Default dither: `floyd_steinberg` or `atkinson` |
| `BINARY_PACK_MODE` | `byte` | `byte` (ESP32 default) or `packed` |
| `FLOYD_STEINBERG_ERROR_DAMPING` | `0.80` | Error diffusion strength (0.0–1.0) |
| `GOOGLE_CLIENT_ID` | *(empty)* | Optional — leave blank for local-only use |
| `GOOGLE_CLIENT_SECRET` | *(empty)* | Optional |
| `GOOGLE_REDIRECT_URI` | `http://localhost:5001/google/callback` | Must match Google Cloud console |

## Image processing pipeline

Implemented in `pi-server/app/processing/`:

1. Load the **original** file from the library (`Image.open` + EXIF transpose)
2. Resize with face-aware focal crop (`focal_crop.py`, default) or contain/stretch
3. Quantize to 6 palette colors with CIE L\*a\*b\* matching (`color.py`, `dither.py`)
4. Apply portrait rotation if configured (`frame_orientation.py`)
5. Pack indices into a raw binary buffer (`binary.py`)
6. Write `latest_frame.bin` and/or `preview.png`

Palette swatches are in `pi-server/app/palette.py`. Tune `EINK_PALETTE_RGB` when you can photograph the actual ink colors on your panel.

## Development

### Run tests

```bash
cd pi-server
pip install -r requirements-dev.txt
make test
```

99+ tests cover processing, gallery/settings routes, frame service, and UI helpers. GitHub Actions runs the same suite on push/PR (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

### Project layout

```
pi-frame/
├── README.md
├── .github/workflows/ci.yml
├── pi-server/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── Makefile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── .env.example
│   ├── app/
│   │   ├── app.py              Flask app + frame endpoints
│   │   ├── gallery_routes.py   Gallery UI and uploads
│   │   ├── settings_routes.py  Settings and quick actions
│   │   ├── google_routes.py    Optional Google Photos import
│   │   ├── frame_service.py    Preview, push, rotation, quick actions
│   │   ├── processing/           Resize, dither, binary export
│   │   └── ui/                 Shared layout and controls
│   └── tests/
└── hardware-drivers/
    ├── esp32_driver/           Production ESP32 firmware (SKU 15823)
    └── README.md               Pi-side SPI notes (legacy / reference)
```

## Implementation status

| Layer | Status |
|---|---|
| Web gallery (upload, preview, push, delete) | Done |
| Daily gallery rotation (`DAILY_CHANGE_TIME`) | Done |
| Dither + orientation + quick actions | Done |
| HTTP frame delivery for ESP32 | Done |
| ESP32 Wi-Fi fetch + panel driver | Done (see `esp32_driver/`) |
| Google Photos import | Done (optional) |
| Unit / route tests + CI | Done |
| Palette calibrated to physical ink | Not yet — uses ideal RGB swatches |
| Pi-native SPI driver (no ESP32) | Experimental skeleton in `hardware-drivers/driver_test.py` |

## Hardware setup

Flash the ESP32 firmware before relying on the physical frame:

1. Edit Wi-Fi and `FRAME_URL` in [`hardware-drivers/esp32_driver/config.h`](hardware-drivers/esp32_driver/config.h) (point at your Pi, e.g. `http://192.168.1.42:5001/get_latest_frame.bin`).
2. Build and upload with Arduino IDE or `arduino-cli` — see [`hardware-drivers/esp32_driver/README.md`](hardware-drivers/esp32_driver/README.md).
3. Push a photo from the gallery, then press the **wake button** on the driver board.

## Troubleshooting

| Problem | Things to check |
|---|---|
| Gallery loads but upload fails | `FLASK_SECRET_KEY` set in `.env`? `app/source_images` exists and is writable? |
| `get_latest_frame.bin` returns 404 | Push a photo first (preview alone does not update the binary unless you use quick actions after a push/preview) |
| ESP32 does not update | `FRAME_URL` in `config.h`, Pi firewall, same LAN, wake button pressed |
| Google import unavailable | Expected if OAuth vars are empty — use gallery upload instead |
| Port already in use on Mac | Use `5001:5000` mapping (default in `docker-compose.yml`) |

## Contributing

Issues and pull requests welcome. Run `make test` in `pi-server/` before submitting.

## License

Add a `LICENSE` file before publishing if you have not already chosen one (MIT and Apache-2.0 are common for hardware-adjacent projects).

# pi-frame

Background image-processing service for a **7.3-inch 6-color e-ink frame** running on a **Raspberry Pi 4 Model B**.

The service runs inside Docker on Raspberry Pi OS (64-bit). It processes travel and environmental photos on a daily schedule, converts them into a binary frame buffer suitable for the display, and serves that file over HTTP for the frame firmware to fetch.

## What it does

1. **Background processing** — A daemon thread wakes up once every 24 hours (configurable), runs the image pipeline in `app/processing.py`, and writes the result to `latest_frame.bin`.
2. **HTTP delivery** — A lightweight Flask server exposes the latest processed frame so the e-ink device can download it on demand.

The dithering pipeline (Atkinson, Floyd-Steinberg, 6-color palette mapping, etc.) is intentionally left as a placeholder in `app/processing.py` so you can drop in your own algorithms.

## Project structure

```
pi-frame/
├── Dockerfile              # Python 3.11 slim image with Pillow, numpy, Flask
├── docker-compose.yml      # Port mapping, timezone, volume mount
├── requirements.txt        # Python dependencies
└── app/
    ├── app.py              # Flask server and background thread
    ├── config.py           # Paths, frame dimensions, intervals
    └── processing.py       # Image processing entry point (your code goes here)
```

## Prerequisites

- Raspberry Pi 4 Model B with Raspberry Pi OS Lite (64-bit)
- [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on the Pi

Verify Docker is available:

```bash
docker --version
docker compose version
```

## Install and run

Clone or copy this repo onto the Pi, then from the project root:

```bash
docker compose up --build -d
```

This will:

- Build the image from `Dockerfile`
- Start the `pi-frame` container on port **5000**
- Mount `./app` into the container at `/app` (live code edits without rebuild)
- Set the container timezone to **Asia/Kolkata**
- Restart the container automatically unless stopped

### View logs

```bash
docker compose logs -f
```

### Stop the service

```bash
docker compose down
```

### Restart after code changes

Because `./app` is volume-mounted, Python file edits take effect on restart:

```bash
docker compose restart
```

Rebuild the image only when `requirements.txt` or `Dockerfile` changes:

```bash
docker compose up --build -d
```

## API

### `GET /get_latest_frame.bin`

Returns the latest processed frame binary.

- **Content-Type:** `application/octet-stream`
- **Source file:** `/app/latest_frame.bin` inside the container
- **404** if no frame has been generated yet

Example from another machine on the network:

```bash
curl -O http://<pi-ip-address>:5000/get_latest_frame.bin
```

## Configuration

Settings live in `app/config.py` and can be overridden with environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `LATEST_FRAME_PATH` | `/app/latest_frame.bin` | Output binary served by the API |
| `SOURCE_IMAGES_DIR` | `/app/source_images` | Directory for input photos |
| `FRAME_WIDTH` | `800` | Target frame width in pixels |
| `FRAME_HEIGHT` | `480` | Target frame height in pixels |
| `PROCESSING_INTERVAL_SECONDS` | `86400` | Seconds between processing cycles (24 h) |
| `FLASK_HOST` | `0.0.0.0` | Flask bind address |
| `FLASK_PORT` | `5000` | Flask listen port |

Example override in `docker-compose.yml`:

```yaml
environment:
  TZ: Asia/Kolkata
  PROCESSING_INTERVAL_SECONDS: 3600
  FRAME_WIDTH: "800"
  FRAME_HEIGHT: "480"
```

## Adding your processing logic

Edit `process_images()` in `app/processing.py`. The intended workflow:

1. Load source images from `SOURCE_IMAGES_DIR`
2. Resize or crop to `FRAME_WIDTH` × `FRAME_HEIGHT`
3. Apply 6-color dithering (Atkinson, Floyd-Steinberg, etc.)
4. Pack pixels into a binary frame buffer
5. Write the result to `LATEST_FRAME_PATH`

Place input images in `app/source_images/` on the host (mapped to `/app/source_images` in the container).

## Remote development

This project is designed for editing on a Mac (or any machine) over SSH into the Pi with Cursor. Edit files under `app/`, then restart the container to pick up changes. No need to rebuild unless dependencies change.

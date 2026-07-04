#!/usr/bin/env python3
"""
Raw SPI/GPIO test skeleton for the 7.3-inch 6-color e-ink display.

Runs directly on the Raspberry Pi host (not inside Docker).
Requires SPI enabled and python3-spidev / python3-rpi.gpio installed.

Usage:
    python3 driver_test.py
"""

import time

# ---------------------------------------------------------------------------
# Pin configuration (BCM numbering — adjust for your panel)
# ---------------------------------------------------------------------------

PIN_RST = 17   # Reset
PIN_DC = 25    # Data/Command select
PIN_CS = 8     # Chip select (SPI CE0)
PIN_BUSY = 24  # Busy signal (input)

SPI_BUS = 0
SPI_DEVICE = 0
SPI_MAX_SPEED_HZ = 4_000_000

# ---------------------------------------------------------------------------
# Hardware initialization
# ---------------------------------------------------------------------------


def init_gpio():
    """
    Configure GPIO pins for the display control signals.

    RST  — output, drives hardware reset
    DC   — output, selects command vs data mode
    BUSY — input,  polled to wait for panel refresh
    """
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(PIN_RST, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(PIN_DC, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_BUSY, GPIO.IN)

    print(f"GPIO initialized — RST={PIN_RST} DC={PIN_DC} BUSY={PIN_BUSY}")


def init_spi():
    """
    Open the SPI bus and configure clock speed and mode.

    Most e-ink controllers use SPI mode 0 (CPOL=0, CPHA=0).
    """
    import spidev

    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEVICE)
    spi.max_speed_hz = SPI_MAX_SPEED_HZ
    spi.mode = 0

    print(f"SPI opened — bus={SPI_BUS} device={SPI_DEVICE} speed={SPI_MAX_SPEED_HZ} Hz")
    return spi


def hardware_reset():
    """Pulse the RST pin to reset the display controller."""
    import RPi.GPIO as GPIO

    GPIO.output(PIN_RST, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(PIN_RST, GPIO.HIGH)
    time.sleep(0.01)
    print("Hardware reset complete")


def wait_until_idle(timeout_s=30):
    """Poll the BUSY pin until the panel finishes its current operation."""
    import RPi.GPIO as GPIO

    deadline = time.monotonic() + timeout_s
    while GPIO.input(PIN_BUSY) == GPIO.HIGH:
        if time.monotonic() > deadline:
            raise TimeoutError("Display BUSY pin did not go idle")
        time.sleep(0.01)


# ---------------------------------------------------------------------------
# Low-level SPI helpers
# ---------------------------------------------------------------------------


def send_command(spi, cmd: int):
    """Send a single command byte (DC = LOW)."""
    import RPi.GPIO as GPIO

    GPIO.output(PIN_DC, GPIO.LOW)
    spi.xfer2([cmd])


def send_data(spi, data: bytes | list[int]):
    """Send one or more data bytes (DC = HIGH)."""
    import RPi.GPIO as GPIO

    GPIO.output(PIN_DC, GPIO.HIGH)
    spi.xfer2(list(data))


# ---------------------------------------------------------------------------
# Test sequence
# ---------------------------------------------------------------------------


def run_display_test(spi):
    """
    Placeholder test sequence.

    Replace with your panel's init command table and a simple
    framebuffer write to verify SPI/GPIO wiring.
    """
    print("Running display test sequence (placeholder)...")

    hardware_reset()
    wait_until_idle()

    # TODO: send panel-specific initialization commands
    # send_command(spi, 0x12)   # SWRESET
    # wait_until_idle()
    # send_command(spi, 0x01)   # Driver output control
    # send_data(spi, [0x27, 0x01, 0x00])

    # TODO: write a test pattern to the display RAM
    # send_command(spi, 0x24)   # Write RAM (black/white)
    # send_data(spi, test_pattern_bytes)

    # TODO: trigger a full refresh
    # send_command(spi, 0x20)   # Master activation
    # wait_until_idle()

    print("Test sequence complete — no errors")


def cleanup(spi):
    """Release SPI and GPIO resources."""
    import RPi.GPIO as GPIO

    spi.close()
    GPIO.cleanup()
    print("SPI and GPIO cleaned up")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    print("=== E-ink display driver test ===")
    spi = None
    try:
        init_gpio()
        spi = init_spi()
        run_display_test(spi)
    except ImportError as exc:
        print(f"Missing dependency: {exc}")
        print("Install with: sudo apt install python3-spidev python3-rpi.gpio")
    except Exception as exc:
        print(f"Test failed: {exc}")
        raise
    finally:
        if spi is not None:
            cleanup(spi)


if __name__ == "__main__":
    main()

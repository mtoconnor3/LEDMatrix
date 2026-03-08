# LEDMatrix

PIO-driven 32x8 LED matrix controller for the Raspberry Pi Pico (RP2040), written in MicroPython.

## Hardware

- **MCU:** Raspberry Pi Pico (RP2040)
- **Display:** 32 columns x 8 rows, 256 LEDs total
- **Shift registers:** 4x 8-bit SIPO chain using TLC6C598 LED drivers
- **Row drivers:** 8 active-low enable lines, multiplexed using 8 GPIO pins from the pico

### Pin mapping

| Signal | GPIO | Purpose |
|--------|-------|---------|
| SCK | 2 | Shift register clock |
| SER_IN | 3 | Shift register serial data (MOSI) |
| RCK | 5 | Shift register latch |
| ROW 0–7 | 6–13 | Row enable (active-low) |

## How it works

The display is multiplexed: one row is lit at a time, relying on persistence of vision to make the whole display appear illuminated at the same time.

Multiplexing is handled by two PIO state machines on PIO0 which frees up the CPU to handle other tasks:

- **SM0 (`_shift_out`)** clocks 32 bits of column data into the shift register chain and pulses the latch pin. It waits for SM1's signal before each shift, and signals SM1 when the latch is done.
- **SM1 (`_row_ctrl`)** disables all rows, signals SM0 to begin shifting, waits for the latch to complete, then enables one row. After a ~128 µs delay (256 PIO cycles), it wraps and repeats for the next row.

The two SMs synchronize via PIO IRQ flags 0 and 1. All display timing is independent of Python execution which ensures the matrix doesn't flicker.

### DMA double-buffering

Two DMA channels continuously feed the PIO TX FIFOs from a 32-byte-aligned framebuffer using ring-wrapped reads — the CPU never touches the FIFOs. A second (back) buffer lets Python prepare the next frame while the current one is being scanned out. Calling `swap()` atomically redirects the column DMA to the new buffer with a single register write.

### Bit remapping

`remap32()` corrects for some PCB wiring order compromises by reversing the last 4 bits of each byte in the row. It runs once when the framebuffer is set to separate it from scanning logic.

## BLE control

The firmware advertises over BLE as `LEDMatrix` and exposes a GATT service for remote frame updates.

| Characteristic | UUID | Direction | Description |
|---|---|---|---|
| Frame RX | `2b2b2b2b-...` | Write | 32 bytes — 8 × uint32 LE, one per row |
| Status TX | `3b3b3b3b-...` | Notify | 4 bytes: connected flag, frame count, error code, reserved |

Send a 32-byte frame to the RX characteristic to update the display. If no client is connected, a fallback animation runs automatically.

## File structure

```
firmware/
  main.py        Entry point — creates SMs, starts display, runs async tasks
  constants.py   Pin assignments, PIO frequency, test patterns
  util.py        PIO programs, remap32(), state machine creation
  matrix.py      LEDMatrix class — framebuffer management and DMA swap
  ble.py         BLE service registration and async task handlers

client/
  __init__.py    Public API re-exports
  client.py      LEDMatrixClient — BLE connect/disconnect, send_frame, read_status
  frames.py      Frame helpers — bitmap_to_frame, frame_to_bitmap, print_frame
  text.py        Text rendering — text_to_columns, preview_text, scroll_text
  animations.py  Animations — blink, row_scan, column_scan, scroll_frame_left
  font.py        8×8 bitmap font (printable ASCII)
  constants.py   UUIDs, ROWS, COLS

notebooks/
  client_demo.ipynb   Demonstrates the client library end-to-end
```

## Firmware usage

The display starts automatically on boot. Connect to `LEDMatrix` over BLE and write a 32-byte frame to update it.

For direct use without BLE:

```python
from util import create_state_machines
from matrix import LEDMatrix

data_sm, row_sm = create_state_machines()
matrix = LEDMatrix(data_sm, row_sm)
matrix.start(initial_framebuffer)

# Write a new frame to the back buffer, then swap:
matrix.set_framebuffer(new_frame)
matrix.swap()
```

The framebuffer is a list of 8 integers, each 32 bits wide (one per row). `set_framebuffer()` writes to the back buffer; `swap()` makes it visible by redirecting DMA.

## Client usage

The `client` package provides a Python BLE client for use on any host machine (macOS, Linux, Windows). Install dependencies with `pip install bleak`.

```python
import asyncio
from client import LEDMatrixClient, bitmap_to_frame, scroll_text, animations

async def main():
    async with await LEDMatrixClient.connect() as matrix:
        # Send a raw frame (8 × uint32, one per row)
        await matrix.send_frame([0xFFFFFFFF] * 8)

        # Or build one from a 2D bitmap
        bitmap = [[0] * 32 for _ in range(8)]
        bitmap[3][10:22] = [1] * 12  # horizontal bar
        await matrix.send_frame(bitmap_to_frame(bitmap))

        # Scroll text across the display
        await scroll_text(matrix, "HELLO WORLD", delay=0.05)

        # Built-in animations
        await animations.row_scan(matrix)
        await animations.blink(matrix, [0xFFFFFFFF] * 8, times=3)

asyncio.run(main())
```

See `notebooks/client_demo.ipynb` for an interactive walkthrough.
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

The display is multiplexed: one row is lit at a time, relying on persistence of vision to make the whole display appear illuminated at the same time..

Multiplexing is handled by two PIO state machines on PIO0 which frees up the CPU to handle other tasks:

- **SM0 (`_shift_out`)** clocks 32 bits of column data into the shift register chain and pulses the latch pin. It waits for SM1's signal before each shift, and signals SM1 when the latch is done.
- **SM1 (`_row_ctrl`)** disables all rows, signals SM0 to begin shifting, waits for the latch to complete, then enables one row. After a ~128 µs delay (256 PIO cycles), it wraps and repeats for the next row.

The two SMs synchronize via PIO IRQ flags 0 and 1. All display timing is independent of Python execution which ensures the matrix doesn't flicker.

### CPU responsibility

Python's only job is keeping the 4-deep TX FIFOs on both SMs fed via `matrix.refill()`. The FIFOs buffer is replenished with `refill()` and can be called asynchronously — just often enough that the FIFOs don't drain completely.

### Bit remapping

`remap32()` corrects for some PCB wiring order compromises by reversing the last 4 bits of each byte in the row. It runs once when the framebuffer is set to separate it from scanning logic. .

## File structure

```
main.py          Entry point — creates SMs, starts display, runs main loop
lib/
  constants.py   Pin assignments, PIO frequency, test patterns
  util.py        PIO programs, remap32(), state machine creation
  matrix.py      LEDMatrix class — framebuffer management and FIFO refill
```

## Usage

```python
from util import create_state_machines
from matrix import LEDMatrix

data_sm, row_sm = create_state_machines()
matrix = LEDMatrix(data_sm, row_sm)
matrix.start(initial_framebuffer)

while True:
    matrix.refill()
    # logic to refill the framebuffer goes here. 
```

The framebuffer is a list of 8 integers, each 32 bits wide (one per row). Update the display at any time with:

```python
matrix.set_framebuffer(new_frame)
```

The new frame takes effect on the next scan cycle. Both `set_framebuffer()` and `refill()` run in the main loop.

## Future work

- **Serial frame streaming:**
- **DMA FIFO feeding:**
- **Double buffering:** 
- **Brightness control:**
# LEDMatrix

PIO-driven 32x8 LED matrix controller for the Raspberry Pi Pico (RP2040), written in MicroPython.

## Hardware

- **MCU:** Raspberry Pi Pico (RP2040)
- **Display:** 32 columns x 8 rows, 256 LEDs total
- **Shift registers:** 4x 8-bit SIPO chain (e.g. 74HC595) for column data
- **Row drivers:** 8 active-low enable lines, accent driven individually

### Pin mapping

| Signal | GPIO | Purpose |
|--------|-------|---------|
| SCK | 2 | Shift register clock |
| SER_IN | 3 | Shift register serial data (MOSI) |
| RCK | 5 | Shift register latch |
| ROW 0–7 | 6–13 | Row enable (active-low) |

## How it works

The display is multiplexed: one row is lit at a time, cycling fast enough (~760 Hz refresh) to appear fully lit via persistence of vision.

Two PIO state machines on PIO0 handle all display timing without CPU involvement:

- **SM0 (`_shift_out`)** clocks 32 bits of column data into the shift register chain and pulses the latch pin. It waits for SM1's signal before each shift, and signals SM1 when the latch is done.
- **SM1 (`_row_ctrl`)** disables all rows, signals SM0 to begin shifting, waits for the latch to complete, then enables one row. After a ~128 µs delay (256 PIO cycles), it wraps and repeats for the next row.

The two SMs synchronize via PIO IRQ flags 0 and 1. All display timing is cycle-accurate and independent of Python execution.

### CPU responsibility

Python's only job is keeping the 4-deep TX FIFOs on both SMs fed via `matrix.refill()`. The FIFOs buffer ~660 µs of scan data (4 rows), so `refill()` does not need to be called with precise timing — just often enough that the FIFOs don't drain completely.

### Bit remapping

`remap32()` corrects for some PCB wiring order compromises by reversing the high nibble bits of each byte. It runs once when the framebuffer is set (not in the scan path).

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
    # application logic here
```

A framebuffer is a list of 8 integers, each 32 bits wide (one per row). Update the display at any time with:

```python
matrix.set_framebuffer(new_frame)
```

The new frame takes effect on the next scan cycle. Both `set_framebuffer()` and `refill()` run in the main loop, so there are no concurrency concerns.

## Future work

- **Serial frame streaming:** Accept frames over UART in the main loop. Parse incoming bytes into framebuffers and call `set_framebuffer()`. The PIO display runs independently, so serial processing can use the full CPU budget (~660 µs between required `refill()` calls).
- **DMA FIFO feeding:** Replace `refill()` with DMA transfers from a ring buffer to both SM FIFOs. This would eliminate the last CPU involvement in the display path entirely.
- **Double buffering:** If `set_framebuffer()` is ever called from an interrupt context (e.g. a UART RX interrupt), a back-buffer/swap pattern would prevent tearing from partial framebuffer updates mid-scan.
- **Brightness control:** The PIO delay loop constant (`set(x, 7)` in `_row_ctrl`) controls display-on time per row. Reducing it dims the display; a second set of delay cycles after row disable would maintain refresh rate while reducing duty cycle.
- **Hardware row decoder:** Replacing the 8 row-enable GPIOs with a 3-to-8 decoder (e.g. 74HC138) would free 5 GPIO pins and allow a single PIO SM to handle the entire display.
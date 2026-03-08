import asyncio
from .constants import ROWS, COLS


async def blink(client, frame: list[int], times: int = 5, on_time: float = 0.3, off_time: float = 0.3):
    """Blink a frame on and off."""
    off = [0] * ROWS
    for _ in range(times):
        await client.send_frame(frame)
        await asyncio.sleep(on_time)
        await client.send_frame(off)
        await asyncio.sleep(off_time)


async def row_scan(client, delay: float = 0.1):
    """Light up one row at a time, top to bottom."""
    for row in range(ROWS):
        frame = [0xFFFFFFFF if r == row else 0 for r in range(ROWS)]
        await client.send_frame(frame)
        await asyncio.sleep(delay)


async def column_scan(client, delay: float = 0.05):
    """Light up one column at a time, left to right."""
    for col in range(COLS):
        frame = [1 << col] * ROWS
        await client.send_frame(frame)
        await asyncio.sleep(delay)


async def scroll_frame_left(client, frame: list[int], delay: float = 0.1, steps: int = 32):
    """Scroll a single frame to the left across the display."""
    for shift in range(steps):
        shifted = [((val >> shift) | (val << (COLS - shift))) & 0xFFFFFFFF for val in frame]
        await client.send_frame(shifted)
        await asyncio.sleep(delay)


async def scan_rows_visual(client, delay: float = 0.1):
    """
    Cycle through rows top-to-bottom. Row N lights the first (N+1) LEDs from
    the left, making each row identifiable by LED count. Runs until cancelled.
    """
    try:
        while True:
            for row in range(ROWS):
                lit_cols = (1 << (row + 1)) - 1
                frame = [lit_cols if r == row else 0 for r in range(ROWS)]
                await client.send_frame(frame)
                await asyncio.sleep(delay)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await client.send_frame([0] * ROWS)

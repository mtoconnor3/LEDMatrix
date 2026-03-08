import struct
from .constants import ROWS, COLS


def frame_to_bytes(frame: list[int]) -> bytes:
    """Pack a list of 8 uint32 row values into 32 bytes (little-endian)."""
    assert len(frame) == ROWS, f"Frame must have {ROWS} rows"
    return struct.pack("<8I", *frame)


def bitmap_to_frame(bitmap: list[list[int]]) -> list[int]:
    """Convert an 8x32 2D array of 0/1 values to a list of 8 uint32 row values."""
    frame = []
    for row in bitmap:
        val = 0
        for col, bit in enumerate(row):
            if bit:
                val |= (1 << col)
        frame.append(val)
    return frame


def frame_to_bitmap(frame: list[int]) -> list[list[int]]:
    """Convert 8 uint32 row values to an 8x32 2D array."""
    return [[(val >> col) & 1 for col in range(COLS)] for val in frame]


def print_frame(frame: list[int]):
    """Pretty-print a frame to the terminal."""
    for val in frame:
        print("".join("#" if (val >> c) & 1 else "." for c in range(COLS)))

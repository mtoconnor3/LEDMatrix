import asyncio
import random

_ROWS = 8
_COLS = 32

# Minimal font — only the characters needed for the lyric phrases below.
# Format matches client/font.py: 8 row bytes, MSB (bit 7) = leftmost pixel.
_FONT = {
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    'A': [0x18, 0x3C, 0x66, 0x7E, 0x66, 0x66, 0x66, 0x00],
    'B': [0x7C, 0x66, 0x66, 0x7C, 0x66, 0x66, 0x7C, 0x00],
    'D': [0x78, 0x6C, 0x66, 0x66, 0x66, 0x6C, 0x78, 0x00],
    'E': [0x7E, 0x60, 0x60, 0x78, 0x60, 0x60, 0x7E, 0x00],
    'F': [0x7E, 0x60, 0x60, 0x78, 0x60, 0x60, 0x60, 0x00],
    'G': [0x3C, 0x66, 0x60, 0x6E, 0x66, 0x66, 0x3C, 0x00],
    'H': [0x66, 0x66, 0x66, 0x7E, 0x66, 0x66, 0x66, 0x00],
    'I': [0x3C, 0x18, 0x18, 0x18, 0x18, 0x18, 0x3C, 0x00],
    'L': [0x60, 0x60, 0x60, 0x60, 0x60, 0x60, 0x7E, 0x00],
    'M': [0x63, 0x77, 0x7F, 0x6B, 0x63, 0x63, 0x63, 0x00],
    'N': [0x66, 0x76, 0x7E, 0x7E, 0x6E, 0x66, 0x66, 0x00],
    'O': [0x3C, 0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x00],
    'R': [0x7C, 0x66, 0x66, 0x7C, 0x78, 0x6C, 0x66, 0x00],
    'S': [0x3C, 0x66, 0x60, 0x3C, 0x06, 0x66, 0x3C, 0x00],
    'T': [0x7E, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x00],
    'U': [0x66, 0x66, 0x66, 0x66, 0x66, 0x66, 0x3C, 0x00],
    'W': [0x63, 0x63, 0x63, 0x6B, 0x7F, 0x77, 0x63, 0x00],
}

_LYRICS = [
    "HARDER BETTER FASTER STRONGER",
    "AROUND THE WORLD",
    "ONE MORE TIME",
]

_FULL_ON = [0xFFFFFFFF] * _ROWS
_ALL_OFF = [0] * _ROWS


def _set(matrix, frame):
    matrix.set_framebuffer(frame)
    matrix.swap()


def _text_to_columns(text):
    """Render text into a list of column bitmasks (bit 0 = top row)."""
    cols = []
    fallback = _FONT[' ']
    for i, ch in enumerate(text):
        glyph = _FONT.get(ch, fallback)
        for c in range(8):
            col_val = 0
            for row in range(8):
                bit = (glyph[row] >> (7 - c)) & 1
                col_val |= bit << row
            cols.append(col_val)
        if i < len(text) - 1:
            cols.append(0)  # 1-column gap between characters
    return cols


async def _scroll_text(matrix, state, text, delay_ms=50):
    cols = _text_to_columns(text)
    padded = [0] * _COLS + cols + [0] * _COLS
    for start in range(len(padded) - _COLS + 1):
        if state.connected:
            return
        window = padded[start:start + _COLS]
        frame = [0] * _ROWS
        for col_idx, col_val in enumerate(window):
            for row in range(_ROWS):
                if (col_val >> row) & 1:
                    frame[row] |= 1 << col_idx
        _set(matrix, frame)
        await asyncio.sleep_ms(delay_ms)


async def _column_sweep(matrix, state, passes=2, delay_ms=30):
    """Bright bar scanning left→right then right→left."""
    for _ in range(passes):
        for col in range(_COLS):
            if state.connected:
                return
            _set(matrix, [1 << col] * _ROWS)
            await asyncio.sleep_ms(delay_ms)
        for col in range(_COLS - 1, -1, -1):
            if state.connected:
                return
            _set(matrix, [1 << col] * _ROWS)
            await asyncio.sleep_ms(delay_ms)


async def _sparkle(matrix, state, duration_ms=3000, delay_ms=80):
    """Random sparse pixels twinkling — AND of two random patterns gives ~25% density."""
    steps = duration_ms // delay_ms
    for _ in range(steps):
        if state.connected:
            return
        frame = [random.getrandbits(32) & random.getrandbits(32) for _ in range(_ROWS)]
        _set(matrix, frame)
        await asyncio.sleep_ms(delay_ms)


async def _row_wipe(matrix, state, passes=2, delay_ms=70):
    """Rows fill top-to-bottom then clear top-to-bottom."""
    for _ in range(passes):
        for row in range(_ROWS):
            if state.connected:
                return
            _set(matrix, [0xFFFFFFFF if r <= row else 0 for r in range(_ROWS)])
            await asyncio.sleep_ms(delay_ms)
        for row in range(_ROWS):
            if state.connected:
                return
            _set(matrix, [0xFFFFFFFF if r > row else 0 for r in range(_ROWS)])
            await asyncio.sleep_ms(delay_ms)


async def _diagonal_cascade(matrix, state, passes=3, delay_ms=35):
    """Multiple pairs of diagonal stripes criss-crossing in opposite directions."""
    stripe_gap = 8
    n_stripes = 4
    total = _COLS + _ROWS - 1  # 39 steps covers the full display

    for _ in range(passes):
        for d in range(total):
            if state.connected:
                return
            frame = [0] * _ROWS
            for k in range(n_stripes):
                off = k * stripe_gap
                for row in range(_ROWS):
                    # "/" stripes sweeping left→right  (col + row = d + off)
                    col = d + off - row
                    if 0 <= col < _COLS:
                        frame[row] |= 1 << col
                    # "\" stripes sweeping right→left  (col - row = (COLS-1) - d + off)
                    col = (_COLS - 1) - d + off + row
                    if 0 <= col < _COLS:
                        frame[row] |= 1 << col
            _set(matrix, frame)
            await asyncio.sleep_ms(delay_ms)


async def _invert_pulse(matrix, state, beats=8, on_ms=150, off_ms=80):
    """Full-on/off beat pattern."""
    for i in range(beats):
        if state.connected:
            return
        _set(matrix, _FULL_ON if i % 2 == 0 else _ALL_OFF)
        await asyncio.sleep_ms(on_ms)
        _set(matrix, _ALL_OFF if i % 2 == 0 else _FULL_ON)
        await asyncio.sleep_ms(off_ms)


async def run_demo(matrix, state):
    """Cycle through helmet animations when no BLE client is connected."""
    while True:
        if state.connected:
            await asyncio.sleep_ms(200)
            continue

        await _scroll_text(matrix, state, _LYRICS[0])
        await _sparkle(matrix, state)
        await _scroll_text(matrix, state, _LYRICS[1])
        await _column_sweep(matrix, state)
        await _scroll_text(matrix, state, _LYRICS[2])
        await _row_wipe(matrix, state)
        await _diagonal_cascade(matrix, state)
        await _invert_pulse(matrix, state)

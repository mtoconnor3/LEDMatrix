import asyncio
from .constants import ROWS, COLS
from .font import FONT_8X8
from .frames import frame_to_bytes


def text_to_columns(text: str, font: dict = FONT_8X8, char_gap: int = 1) -> list[int]:
    """
    Render a text string into a list of column bitmasks.

    Each column is an 8-bit integer where bit 0 = top row, bit 7 = bottom row.
    Characters are drawn left-to-right with `char_gap` blank columns between
    them. Unknown characters fall back to a space.
    """
    columns = []
    fallback = font.get(' ', [0] * 8)
    for i, ch in enumerate(text):
        glyph = font.get(ch, fallback)
        for col in range(8):
            col_val = 0
            for row in range(8):
                bit = (glyph[row] >> (7 - col)) & 1
                col_val |= bit << row
            columns.append(col_val)
        if i < len(text) - 1:
            columns.extend([0] * char_gap)
    return columns


def preview_text(text: str, font: dict = FONT_8X8, char_gap: int = 1):
    """Print a terminal preview of the rendered text."""
    cols = text_to_columns(text, font, char_gap)
    print(f"Rendered '{text}' → {len(cols)} columns\n")
    for row in range(ROWS):
        print("".join("#" if (c >> row) & 1 else "." for c in cols))


async def scroll_text(
    client,
    text: str,
    font: dict = FONT_8X8,
    delay: float = 0.05,
    char_gap: int = 1,
    repeat: int = 1,
):
    """
    Scroll text across the 8x32 LED matrix from right to left.

    The text enters from the right edge and exits off the left edge.

    Args:
        client:   Connected LEDMatrixClient.
        text:     String to display.
        font:     Glyph dict (defaults to FONT_8X8).
        delay:    Seconds between column shifts — controls scroll speed.
        char_gap: Blank columns inserted between characters (default 1).
        repeat:   Number of times to scroll the full message.
    """
    text_cols = text_to_columns(text, font, char_gap)
    padded = [0] * COLS + text_cols + [0] * COLS

    for _ in range(repeat):
        for start in range(len(padded) - COLS + 1):
            window = padded[start: start + COLS]
            frame = [0] * ROWS
            for col_idx, col_val in enumerate(window):
                for row in range(ROWS):
                    if (col_val >> row) & 1:
                        frame[row] |= 1 << col_idx
            await client.send_frame(frame)
            await asyncio.sleep(delay)

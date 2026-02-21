from util import remap32
import array
import uctypes
import rp2
from machine import mem32

# PIO0 TX FIFO hardware addresses
PIO0_TXF0 = 0x50200010  # SM0
PIO0_TXF1 = 0x50200014  # SM1

# DMA register base
DMA_BASE = 0x50000000
DMA_CH_STRIDE = 0x40  # register block size per channel

# PIO0 TX data-request indices
DREQ_PIO0_TX0 = 0
DREQ_PIO0_TX1 = 1


def _alloc_aligned(count, alignment=32):
    """Allocate *count* uint32 values at an *alignment*-byte boundary.

    Returns ``(raw_array, aligned_address)``.  The caller must keep
    *raw_array* alive to prevent the GC from reclaiming the memory.
    """
    pad = alignment // 4
    raw = array.array('I', [0] * (count + pad))
    addr = uctypes.addressof(raw)
    offset = (alignment - (addr % alignment)) % alignment
    return raw, addr + offset


class LEDMatrix:
    """DMA-driven double-buffered 32×8 LED matrix controller.

    Two DMA channels continuously feed the PIO TX FIFOs using ring-wrapped
    reads over 32-byte (8-word) aligned buffers.  The CPU never touches the
    FIFOs — it only writes pixel data into the *back* buffer and calls
    ``swap()`` to make it visible.
    """

    def __init__(self, data_sm, row_sm):
        self._data_sm = data_sm
        self._row_sm = row_sm

        # Double framebuffer — 32-byte aligned for DMA ring wrapping
        self._fb_raw_a, self._fb_a = _alloc_aligned(8)
        self._fb_raw_b, self._fb_b = _alloc_aligned(8)
        self._front = self._fb_a   # being scanned out by DMA
        self._back = self._fb_b    # CPU writes here

        # Row-enable patterns (static, single buffer)
        self._row_raw, self._row_addr = _alloc_aligned(8)
        for i in range(8):
            mem32[self._row_addr + i * 4] = ~(1 << i) & 0xFF

        # Claim two DMA channels
        self._col_dma = rp2.DMA()
        self._row_dma = rp2.DMA()

    # ── public API ────────────────────────────────────────────────

    def start(self, framebuffer=None):
        """Configure DMA and start the display.

        If *framebuffer* is given it is written to the front buffer so it
        is visible immediately.
        """
        if framebuffer is not None:
            self._write_buf(self._front, framebuffer)

        # Column data → SM0 TX FIFO
        self._col_dma.config(
            read=self._front,
            write=PIO0_TXF0,
            count=0xFFFFFFFF,
            ctrl=self._col_dma.pack_ctrl(
                size=2,            # 32-bit transfers
                inc_read=True,
                inc_write=False,
                treq_sel=DREQ_PIO0_TX0,
                ring_sel=False,    # ring on read address
                ring_size=5,       # 2^5 = 32 bytes = 8 words
                chain_to=self._col_dma.channel,  # no chaining
            ),
            trigger=False,
        )

        # Row patterns → SM1 TX FIFO
        self._row_dma.config(
            read=self._row_addr,
            write=PIO0_TXF1,
            count=0xFFFFFFFF,
            ctrl=self._row_dma.pack_ctrl(
                size=2,
                inc_read=True,
                inc_write=False,
                treq_sel=DREQ_PIO0_TX1,
                ring_sel=False,
                ring_size=5,
                chain_to=self._row_dma.channel,
            ),
            trigger=False,
        )

        # DMA first (pre-fills FIFOs), then PIO
        self._col_dma.active(1)
        self._row_dma.active(1)
        self._data_sm.active(1)
        self._row_sm.active(1)

    def stop(self):
        """Halt display: PIO first, then DMA."""
        self._data_sm.active(0)
        self._row_sm.active(0)
        self._col_dma.active(0)
        self._row_dma.active(0)

    def set_framebuffer(self, fb):
        """Write a new frame into the back buffer (not yet visible)."""
        self._write_buf(self._back, fb)

    def swap(self):
        """Make the back buffer visible.

        Atomically redirects the column DMA read address to the other
        buffer.  The old front buffer becomes the new back buffer.
        """
        self._front, self._back = self._back, self._front
        ch = self._col_dma.channel
        mem32[DMA_BASE + ch * DMA_CH_STRIDE] = self._front

    def close(self):
        """Stop display and release DMA channels."""
        self.stop()
        self._col_dma.close()
        self._row_dma.close()

    # ── internals ─────────────────────────────────────────────────

    @staticmethod
    def _write_buf(addr, fb):
        """Write an 8-element framebuffer list into an aligned DMA buffer."""
        for i in range(8):
            mem32[addr + i * 4] = remap32(fb[i])

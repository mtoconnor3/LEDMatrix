from util import remap32
import constants


class LEDMatrix:
    def __init__(self, data_sm, row_sm):
        self._data_sm = data_sm
        self._row_sm = row_sm
        self._mapped_fb = [0] * 8
        self._row_patterns = [~(1 << i) & 0xFF for i in range(8)]
        self._fill_row = 0

    def start(self, framebuffer=None):
        if framebuffer is not None:
            self._mapped_fb = [remap32(v) for v in framebuffer]

        # Pre-fill both FIFOs (4 deep)
        for i in range(4):
            self._data_sm.put(self._mapped_fb[i])
            self._row_sm.put(self._row_patterns[i])
        self._fill_row = 4

        self._data_sm.active(1)
        self._row_sm.active(1)

    def stop(self):
        self._data_sm.active(0)
        self._row_sm.active(0)

    def set_framebuffer(self, fb):
        self._mapped_fb = [remap32(v) for v in fb]

    def refill(self):
        """Call regularly to keep PIO FIFOs fed. Safe to call as often as needed."""
        while self._data_sm.tx_fifo() < 4 and self._row_sm.tx_fifo() < 4:
            self._data_sm.put(self._mapped_fb[self._fill_row])
            self._row_sm.put(self._row_patterns[self._fill_row])
            self._fill_row = (self._fill_row + 1) % 8

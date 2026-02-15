from machine import Pin
from util import write32
import constants
import time

class LEDMatrix:
    def __init__(self, spi_bus, latch_pin):
        self.spi_bus = spi_bus
        self.latch_pin = latch_pin

        self.rows = [LEDRow(pin) for pin in constants.ROW_ENABLE_PINS]
        self.num_rows = len(self.rows)

        self.current_row = 0

        # Disable all on startup
        self.disable_all()

    def disable_all(self):
        for row in self.rows:
            row.disable()

    def scan_once(self, framebuffer):
        """
        Call this continuously.
        framebuffer = list of 8 integers (32-bit)
        """

        # 1. Disable all rows
        self.disable_all()

        # 2. Shift next row's data
        write32(framebuffer[self.current_row],
                spi=self.spi_bus,
                latch_pin=self.latch_pin)

        # 3. Enable that row
        self.rows[self.current_row].enable()

        # 4. Advance row pointer
        self.current_row = (self.current_row + 1) % self.num_rows


class LEDRow:
    def __init__(self, enable_pin):
        self.enable_pin = Pin(enable_pin, Pin.OUT)
        self.disable()

    def enable(self):
        self.enable_pin.value(0)

    def disable(self):
        self.enable_pin.value(1)
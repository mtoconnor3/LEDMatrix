import time
from machine import Pin
from util import get_spi
from matrix import LEDMatrix
import constants

spi = get_spi()
latch = Pin(constants.RCK, Pin.OUT)

matrix = LEDMatrix(spi, latch)

framebuffer = constants.TEST_PATTERN_ALL_ON

# Target: ~1 kHz total refresh
# 8 rows → ~8000 row scans/sec
SCAN_DELAY_US = 1_000_000 // 1600  # 100 µs per row → 1.25 kHz refresh

while True:
    matrix.scan_once(framebuffer)
    time.sleep_us(SCAN_DELAY_US)
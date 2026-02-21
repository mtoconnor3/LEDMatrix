from util import create_state_machines
from matrix import LEDMatrix
import constants
import time
import random

def random_hex32_list():
    return [random.getrandbits(32) for _ in range(8)]

def bitwise_and(old, new):
    return [a ^ b for a,b in zip(old, new)]

# Fill the buffer with something
oldbuffer = constants.TEST_PATTERN_ALL_ON

# Set up the display
data_sm, row_sm = create_state_machines()
matrix = LEDMatrix(data_sm, row_sm)
matrix.start(oldbuffer)

# DMA feeds both PIO FIFOs automatically — the CPU is completely free.

now = time.ticks_us()
while True:
    # Flip some bits occasionally
    if time.ticks_diff(time.ticks_us(), now) >= 100000:
        newbuffer = bitwise_and(oldbuffer, random_hex32_list())
        matrix.set_framebuffer(newbuffer)
        matrix.swap()
        oldbuffer = newbuffer
        now = time.ticks_us()

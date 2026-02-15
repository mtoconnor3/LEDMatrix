import constants
from machine import Pin, SPI
import _thread
import time

enable = Pin(16, Pin.OUT)

def remap32(value):
    out = 0

    for byte_index in range(4):
        b = (value >> (byte_index * 8)) & 0xFF

        low  = b & 0x0F
        high = (b >> 4) & 0x0F

        rev = (
            ((high & 0b0001) << 3) |
            ((high & 0b0010) << 1) |
            ((high & 0b0100) >> 1) |
            ((high & 0b1000) >> 3)
        )

        fixed = low | (rev << 4)
        out |= fixed << (byte_index * 8)

    return out

def write_shift_register(data, spi, latch_pin):
    spi.write(data)
    latch_pin.value(1)
    time.sleep_us(5)
    latch_pin.value(0)

def write32(value, **kwargs):
    fixed = remap32(value)
    data = fixed.to_bytes(4, 'big')
    write_shift_register(data, **kwargs)
    
def get_spi():
    spi = SPI(0,
          baudrate=1_000_000,
          polarity=0,
          phase=0,
          sck=Pin(constants.SCK),
          mosi=Pin(constants.SER_IN),
          miso=Pin(constants.SER_OUT))
    
    return spi

def pwm_thread():
    period_us = int(1_000_000 / constants.FREQ)
    high_time = int(period_us * constants.DUTY)
    low_time  = period_us - high_time

    while True:
        enable.value(1)
        time.sleep_us(high_time)
        enable.value(0)
        time.sleep_us(low_time)

# Start PWM in separate thread
#_thread.start_new_thread(pwm_thread, ())
from machine import Pin, SPI
import time
import random
import _thread

from machine import Pin, PWM

enable = Pin(16, Pin.OUT)

# Software PWM parameters
FREQ = 500  # Hz
DUTY = 1 - (1/8)  # 12.5%

def pwm_thread():
    period_us = int(1_000_000 / FREQ)
    high_time = int(period_us * DUTY)
    low_time  = period_us - high_time

    while True:
        enable.value(1)
        time.sleep_us(high_time)
        enable.value(0)
        time.sleep_us(low_time)

# Start PWM in separate thread
_thread.start_new_thread(pwm_thread, ())

spi = SPI(0,
          baudrate=1_000_000,
          polarity=0,
          phase=0,
          sck=Pin(2),
          mosi=Pin(3),
          miso=Pin(4))

latch = Pin(5, Pin.OUT)

def write_shift_register(data):
    spi.write(data)
    latch.value(1)
    time.sleep_us(2)
    latch.value(0)

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

def write32(value):
    fixed = remap32(value)                 # remap FIRST
    data = fixed.to_bytes(4, 'big')        # then convert to bytes
    write_shift_register(data)

shadow = 0
while True:
    
    for i in range(2**32):
        #shadow |= (1 << i)
        #write32(shadow)
        write32(i)
        #write32(0xffffffff)
        #time.sleep(0.1)

    shadow = 0
    write32(shadow)

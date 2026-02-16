import rp2
from machine import Pin
import constants


@rp2.asm_pio(
    out_init=rp2.PIO.OUT_LOW,
    sideset_init=rp2.PIO.OUT_LOW,
    set_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
)
def _shift_out():
    """Clock out 32 bits, latch, signal row SM."""
    wrap_target()
    wait(1, irq, 1)         .side(0)   # Wait for row SM: rows disabled
    pull(block)              .side(0)   # Get column data from FIFO
    set(x, 31)              .side(0)   # 32-bit counter
    label("bitloop")
    out(pins, 1)            .side(0)   # Data out, SCK low
    jmp(x_dec, "bitloop")   .side(1)   # SCK high (rising edge clocks shift reg)
    set(pins, 1)            .side(0)   # RCK high — latch
    set(pins, 0)            .side(0)   # RCK low
    irq(0)                  .side(0)   # Signal row SM: latch done
    wrap()


@rp2.asm_pio(
    out_init=(rp2.PIO.OUT_HIGH,) * 8,
    out_shiftdir=rp2.PIO.SHIFT_RIGHT,
)
def _row_ctrl():
    """Cycle row enables in lockstep with data SM."""
    wrap_target()
    mov(pins, invert(null))            # All rows disabled
    pull(block)                        # Get row pattern (stalls if FIFO empty — safe, rows off)
    irq(1)                             # Signal data SM: safe to shift
    wait(1, irq, 0)                    # Wait for data SM: latch done
    out(pins, 8)                       # Enable one row
    set(x, 7)                          # Display delay counter
    label("delay")
    jmp(x_dec, "delay")        [31]    # 8 × 32 = 256 cycles ≈ 128 µs at 2 MHz
    wrap()


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


def create_state_machines():
    data_sm = rp2.StateMachine(
        0,
        _shift_out,
        freq=constants.PIO_FREQ,
        out_base=Pin(constants.SER_IN),
        sideset_base=Pin(constants.SCK),
        set_base=Pin(constants.RCK),
    )
    row_sm = rp2.StateMachine(
        1,
        _row_ctrl,
        freq=constants.PIO_FREQ,
        out_base=Pin(constants.ROW_ENABLE_PINS[0]),
    )
    return data_sm, row_sm

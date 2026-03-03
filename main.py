import asyncio
import random
from util import create_state_machines
from matrix import LEDMatrix
from ble import DisplayState, register_services, peripheral_task, rx_handler_task
import constants


async def frame_applicator_task(matrix, state):
    """Wait for new frames from BLE and apply them to the matrix."""
    while True:
        await state.frame_event.wait()
        state.frame_event.clear()

        frame = state.frame
        if frame is not None:
            matrix.set_framebuffer(frame)
            matrix.swap()


async def demo_task(matrix, state):
    """Fallback animation when no BLE client is connected."""
    fb = list(constants.TEST_PATTERN_ALL_ON)
    matrix.set_framebuffer(fb)
    matrix.swap()

    while True:
        if state.connected:
            await asyncio.sleep_ms(500)
            continue

        fb = [a ^ random.getrandbits(32) for a in fb]
        matrix.set_framebuffer(fb)
        matrix.swap()
        await asyncio.sleep_ms(100)


async def main():
    # Hardware setup (unchanged)
    data_sm, row_sm = create_state_machines()
    matrix = LEDMatrix(data_sm, row_sm)
    matrix.start(constants.TEST_PATTERN_ALL_ON)

    # BLE setup
    state = DisplayState()
    rx_char, tx_char = register_services()

    await asyncio.gather(
        peripheral_task(state, rx_char, tx_char),
        rx_handler_task(state, rx_char, tx_char),
        frame_applicator_task(matrix, state),
        demo_task(matrix, state),
    )


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass

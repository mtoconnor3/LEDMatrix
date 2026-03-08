import bluetooth
import aioble
import asyncio
import struct

# Custom 128-bit UUIDs
_MATRIX_SERVICE_UUID = bluetooth.UUID("1b1b1b1b-1b1b-1b1b-1b1b-1b1b1b1b1b1b")
_FRAME_RX_UUID = bluetooth.UUID("2b2b2b2b-2b2b-2b2b-2b2b-2b2b2b2b2b2b")
_STATUS_TX_UUID = bluetooth.UUID("3b3b3b3b-3b3b-3b3b-3b3b-3b3b3b3b3b3b")

_ADV_INTERVAL_US = 250_000
_ADV_NAME = "LEDMatrix"
_DESIRED_MTU = 48  # 33 payload + ATT overhead + margin

# Status error codes
_ERR_NONE = 0x00
_ERR_BAD_LENGTH = 0x01


class DisplayState:
    """Shared state between BLE tasks and the display applicator."""

    def __init__(self):
        self.connected = False
        self.frame = None
        self.frame_count = 0
        self.last_error = _ERR_NONE
        self.frame_event = asyncio.Event()


def _parse_frame(data):
    """Parse raw bytes into a list of 8 uint32 values, or None if invalid."""
    if len(data) == 32:
        return list(struct.unpack("<8I", data))
    return None


def _update_status(tx_char, state):
    """Write current status to the TX characteristic."""
    status = struct.pack(
        "<BBBB",
        0x01 if state.connected else 0x00,
        state.frame_count & 0xFF,
        state.last_error,
        0x00,
    )
    tx_char.write(status, send_update=True)


def register_services():
    """Create and register the GATT service. Returns (rx_char, tx_char)."""
    aioble.config(mtu=_DESIRED_MTU)

    service = aioble.Service(_MATRIX_SERVICE_UUID)

    rx_char = aioble.BufferedCharacteristic(
        service,
        _FRAME_RX_UUID,
        write=True,
        max_len=33,
        capture=True,
    )

    tx_char = aioble.Characteristic(
        service,
        _STATUS_TX_UUID,
        read=True,
        notify=True,
        initial=b"\x00\x00\x00\x00",
    )

    aioble.register_services(service)
    return rx_char, tx_char


async def peripheral_task(state, rx_char, tx_char):
    """Advertise, accept connections, manage lifecycle. Runs forever."""
    while True:
        print("BLE: advertising...")
        connection = await aioble.advertise(
            _ADV_INTERVAL_US,
            name=_ADV_NAME,
            services=[_MATRIX_SERVICE_UUID],
        )
        print("BLE: connected from", connection.device)
        state.connected = True
        _update_status(tx_char, state)

        # Poll for disconnect (catches silent disconnects on Pico W)
        try:
            while connection.is_connected():
                await asyncio.sleep_ms(500)
        except Exception as e:
            print("BLE: connection error:", e)
        finally:
            print("BLE: disconnected")
            state.connected = False
            _update_status(tx_char, state)


async def rx_handler_task(state, rx_char, tx_char):
    """Wait for writes on the RX characteristic and update display state."""
    while True:
        try:
            connection, data = await rx_char.written(timeout_ms=1000)
        except asyncio.TimeoutError:
            continue

        frame = _parse_frame(data)
        if frame is not None:
            state.frame = frame
            state.frame_count = (state.frame_count + 1) & 0xFF
            state.last_error = _ERR_NONE
            state.frame_event.set()
        else:
            state.last_error = _ERR_BAD_LENGTH
            print("BLE: bad frame length:", len(data))

        _update_status(tx_char, state)

import struct
from bleak import BleakClient, BleakScanner
from .constants import DEVICE_NAME, FRAME_RX_UUID, STATUS_TX_UUID, BRIGHTNESS_RX_UUID
from .frames import frame_to_bytes


class LEDMatrixClient:
    """BLE client for the LED matrix.

    Use as an async context manager to handle connect/disconnect automatically::

        async with await LEDMatrixClient.connect() as matrix:
            await matrix.send_frame([0xFFFFFFFF] * 8)

    Or manage the lifecycle manually::

        matrix = await LEDMatrixClient.connect()
        await matrix.send_frame([0xFFFFFFFF] * 8)
        await matrix.disconnect()
    """

    def __init__(self, client: BleakClient):
        self._client = client

    # ── lifecycle ─────────────────────────────────────────────────

    @classmethod
    async def connect(cls, name: str = DEVICE_NAME, timeout: float = 10.0) -> "LEDMatrixClient":
        """Scan for the device and return a connected client."""
        print(f"Scanning for '{name}'...")
        device = await BleakScanner.find_device_by_name(name, timeout=timeout)
        if device is None:
            raise RuntimeError(f"Device '{name}' not found. Make sure it's powered on and advertising.")
        print(f"Found: {device.name} ({str(device.address)[:10]}...)")
        client = BleakClient(device)
        await client.connect()
        print(f"Connected: {client.is_connected}")
        return cls(client)

    async def disconnect(self):
        """Disconnect from the device."""
        await self._client.disconnect()
        print(f"Disconnected: {not self._client.is_connected}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected

    # ── core operations ───────────────────────────────────────────

    async def send_frame(self, frame: list[int]):
        """Send 8 uint32 row values to the display."""
        await self._client.write_gatt_char(FRAME_RX_UUID, frame_to_bytes(frame))

    async def set_brightness(self, level: int):
        """Set display brightness. level must be 0–255 (0 = off, 255 = full)."""
        if not 0 <= level <= 255:
            raise ValueError(f"brightness level must be 0-255, got {level}")
        await self._client.write_gatt_char(BRIGHTNESS_RX_UUID, bytes([level]))

    async def read_status(self) -> dict:
        """Read and parse the status characteristic."""
        data = await self._client.read_gatt_char(STATUS_TX_UUID)
        connected, frame_count, last_error, brightness = struct.unpack("<BBBB", data)
        return {
            "connected": bool(connected),
            "frame_count": frame_count,
            "last_error": last_error,
            "brightness": brightness,
        }

    async def subscribe_status(self, callback):
        """Subscribe to status notifications. callback receives parsed dict."""
        def _cb(sender, data):
            connected, frame_count, last_error, brightness = struct.unpack("<BBBB", data)
            callback({
                "connected": bool(connected),
                "frame_count": frame_count,
                "last_error": last_error,
                "brightness": brightness,
            })
        await self._client.start_notify(STATUS_TX_UUID, _cb)

    async def unsubscribe_status(self):
        """Stop status notifications."""
        await self._client.stop_notify(STATUS_TX_UUID)

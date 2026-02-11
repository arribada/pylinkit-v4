from enum import Enum


class TransportType(Enum):
    BLE = 'ble'
    USB = 'usb'
    UART = 'uart'


def create_transport(transport_type, **kwargs):
    """Factory function to create the appropriate transport."""
    if transport_type == TransportType.BLE:
        from .ble import BLETransport
        return BLETransport()
    elif transport_type == TransportType.USB:
        from .serial import SerialTransport
        return SerialTransport(read_only=False)
    elif transport_type == TransportType.UART:
        from .serial import SerialTransport
        return SerialTransport(read_only=kwargs.get('read_only', True))
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")

# ui.widgets package
from .connection_card import ConnectionCardWidget
from .status_card import StatusCardWidget
from .coordinates_card import CoordinatesCardWidget
from .capture_card import CaptureCardWidget
from .gcp_table import GCPTableWidget

__all__ = [
    "ConnectionCardWidget",
    "StatusCardWidget",
    "CoordinatesCardWidget",
    "CaptureCardWidget",
    "GCPTableWidget"
]

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from gps.nmea_parser import GNSSData


@dataclass
class GCPPoint:
    point_id: str
    latitude: float
    longitude: float
    height: float                    # ground mark: antenna height already removed
    h_accuracy: float
    v_accuracy: float
    fix_status: str
    satellites: int
    timestamp: datetime = field(default_factory=datetime.now)
    sample_count: int = 1
    # Height as reported at the antenna phase centre, and the pole/tripod offset
    # subtracted to get from there down to the mark. Both are kept so a wrong
    # antenna height can be corrected afterwards without re-surveying.
    raw_height: float = 0.0
    antenna_height: float = 0.0
    # True when the operator saved this point below RTK Fixed quality.
    quality_override: bool = False

    def to_csv_row(self) -> dict:
        """Returns a dict matching Pix4D CSV header fields."""
        return {
            "Point": self.point_id,
            "Latitude": f"{self.latitude:.9f}",
            "Longitude": f"{self.longitude:.9f}",
            "EllipsoidalHeight_WGS84": f"{self.height:.3f}",
            "AntennaHeight": f"{self.antenna_height:.3f}",
            "RawAntennaHeight": f"{self.raw_height:.3f}",
            "HorizontalAccuracy": f"{self.h_accuracy:.3f}",
            "VerticalAccuracy": f"{self.v_accuracy:.3f}",
            "Fix": self.fix_status,
            "QualityOverride": "YES" if self.quality_override else "",
            "Satellites": self.satellites,
            "Time": self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }

    def to_dict(self) -> dict:
        """Serialises for autosave. Timestamp goes out as ISO-8601."""
        return {
            "point_id": self.point_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "height": self.height,
            "h_accuracy": self.h_accuracy,
            "v_accuracy": self.v_accuracy,
            "fix_status": self.fix_status,
            "satellites": self.satellites,
            "timestamp": self.timestamp.isoformat(),
            "sample_count": self.sample_count,
            "raw_height": self.raw_height,
            "antenna_height": self.antenna_height,
            "quality_override": self.quality_override,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GCPPoint":
        """Rebuilds a point from autosaved JSON, tolerating older files."""
        ts = d.get("timestamp")
        try:
            stamp = datetime.fromisoformat(ts) if ts else datetime.now()
        except (TypeError, ValueError):
            stamp = datetime.now()
        return cls(
            point_id=d.get("point_id", "GCP001"),
            latitude=float(d.get("latitude", 0.0)),
            longitude=float(d.get("longitude", 0.0)),
            height=float(d.get("height", 0.0)),
            h_accuracy=float(d.get("h_accuracy", 0.0)),
            v_accuracy=float(d.get("v_accuracy", 0.0)),
            fix_status=d.get("fix_status", "No Fix"),
            satellites=int(d.get("satellites", 0)),
            timestamp=stamp,
            sample_count=int(d.get("sample_count", 1)),
            raw_height=float(d.get("raw_height", d.get("height", 0.0))),
            antenna_height=float(d.get("antenna_height", 0.0)),
            quality_override=bool(d.get("quality_override", False)),
        )


class GCPAverager:
    """Collects GNSS position samples over a target duration and computes average position."""

    # A capture is considered stalled if no GNSS update arrives for this long.
    STALL_TIMEOUT_SEC = 5.0

    def __init__(self):
        self.active: bool = False
        self.point_id: str = ""
        self.duration_sec: int = 15
        self.start_time: Optional[float] = None
        self.last_data_time: Optional[float] = None
        self.antenna_height: float = 0.0
        self.samples: List[GNSSData] = []

    def start(self, point_id: str, duration_sec: int = 15, antenna_height: float = 0.0):
        self.active = True
        self.point_id = point_id
        self.duration_sec = duration_sec
        self.antenna_height = antenna_height
        self.start_time = datetime.now().timestamp()
        self.last_data_time = self.start_time
        self.samples.clear()

    def cancel(self):
        """Abandons an in-flight capture and discards its samples."""
        self.active = False
        self.start_time = None
        self.last_data_time = None
        self.samples.clear()

    def is_stalled(self) -> bool:
        """True if a capture is running but the GNSS stream has gone quiet."""
        if not self.active or not self.last_data_time:
            return False
        return (datetime.now().timestamp() - self.last_data_time) > self.STALL_TIMEOUT_SEC

    def add_sample(self, gnss_data: GNSSData) -> bool:
        """Adds a sample if active. Returns True when target duration is reached."""
        if not self.active:
            return False

        self.last_data_time = datetime.now().timestamp()

        if gnss_data.is_valid:
            self.samples.append(gnss_data)

        elapsed = datetime.now().timestamp() - self.start_time
        if elapsed >= self.duration_sec:
            self.active = False
            return True
        return False

    def get_progress_percent(self) -> float:
        if not self.active or not self.start_time:
            return 0.0
        elapsed = datetime.now().timestamp() - self.start_time
        pct = (elapsed / float(self.duration_sec)) * 100.0
        return min(100.0, max(0.0, pct))

    def get_remaining_seconds(self) -> int:
        if not self.active or not self.start_time:
            return 0
        elapsed = datetime.now().timestamp() - self.start_time
        rem = self.duration_sec - int(elapsed)
        return max(0, rem)

    def compute_average(self) -> Optional[GCPPoint]:
        """Computes arithmetic average of collected samples."""
        if not self.samples:
            return None

        count = len(self.samples)
        avg_lat = sum(s.latitude for s in self.samples) / count
        avg_lon = sum(s.longitude for s in self.samples) / count
        avg_alt = sum(s.altitude for s in self.samples) / count
        avg_h_acc = sum(s.h_accuracy for s in self.samples) / count
        avg_v_acc = sum(s.v_accuracy for s in self.samples) / count
        max_sats = max(s.satellites for s in self.samples)

        # Determine best fix status
        fix_statuses = [s.fix_status for s in self.samples]
        if "RTK Fixed" in fix_statuses:
            best_fix = "RTK Fixed"
        elif "RTK Float" in fix_statuses:
            best_fix = "RTK Float"
        elif "3D Fix" in fix_statuses:
            best_fix = "3D Fix"
        else:
            best_fix = "No Fix"

        # The receiver reports the antenna phase centre; the GCP is the mark on
        # the ground, so the pole height comes off before the point is recorded.
        ground_alt = avg_alt - self.antenna_height

        return GCPPoint(
            point_id=self.point_id,
            latitude=round(avg_lat, 9),
            longitude=round(avg_lon, 9),
            height=round(ground_alt, 3),
            raw_height=round(avg_alt, 3),
            antenna_height=round(self.antenna_height, 3),
            h_accuracy=round(avg_h_acc, 3),
            v_accuracy=round(avg_v_acc, 3),
            fix_status=best_fix,
            satellites=max_sats,
            timestamp=datetime.now(),
            sample_count=count
        )

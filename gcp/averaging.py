from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from gps.nmea_parser import GNSSData


@dataclass
class GCPPoint:
    point_id: str
    latitude: float
    longitude: float
    height: float
    h_accuracy: float
    v_accuracy: float
    fix_status: str
    satellites: int
    timestamp: datetime = field(default_factory=datetime.now)
    sample_count: int = 1

    def to_csv_row(self) -> dict:
        """Returns a dict matching Pix4D CSV header fields."""
        return {
            "Point": self.point_id,
            "Latitude": f"{self.latitude:.9f}",
            "Longitude": f"{self.longitude:.9f}",
            "Height": f"{self.height:.3f}",
            "HorizontalAccuracy": f"{self.h_accuracy:.3f}",
            "VerticalAccuracy": f"{self.v_accuracy:.3f}",
            "Fix": self.fix_status,
            "Satellites": self.satellites,
            "Time": self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }


class GCPAverager:
    """Collects GNSS position samples over a target duration and computes average position."""

    def __init__(self):
        self.active: bool = False
        self.point_id: str = ""
        self.duration_sec: int = 15
        self.start_time: Optional[float] = None
        self.samples: List[GNSSData] = []

    def start(self, point_id: str, duration_sec: int = 15):
        self.active = True
        self.point_id = point_id
        self.duration_sec = duration_sec
        self.start_time = datetime.now().timestamp()
        self.samples.clear()

    def add_sample(self, gnss_data: GNSSData) -> bool:
        """Adds a sample if active. Returns True when target duration is reached."""
        if not self.active:
            return False

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

        return GCPPoint(
            point_id=self.point_id,
            latitude=round(avg_lat, 9),
            longitude=round(avg_lon, 9),
            height=round(avg_alt, 3),
            h_accuracy=round(avg_h_acc, 3),
            v_accuracy=round(avg_v_acc, 3),
            fix_status=best_fix,
            satellites=max_sats,
            timestamp=datetime.now(),
            sample_count=count
        )

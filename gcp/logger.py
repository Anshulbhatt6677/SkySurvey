import json
import os
import tempfile
from typing import List, Optional

from .averaging import GCPPoint


def default_session_path() -> str:
    """Autosave location, following XDG on Linux and falling back elsewhere."""
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "SkySurvey", "session.json")


class GCPLogger:
    """Manages logged GCP points, mirroring every change to disk.

    Field survey data cannot live only in memory: a crash, a dropped USB link or
    a closed lid would otherwise cost a whole site's worth of points. Every
    mutation is written through immediately, and the last session is reloaded on
    startup so an interrupted survey can be continued rather than repeated.
    """

    def __init__(self, session_path: Optional[str] = None, autoload: bool = True):
        self.points: List[GCPPoint] = []
        self.next_index: int = 1
        self.session_path = session_path or default_session_path()
        self.last_error: Optional[str] = None
        self.recovered_count: int = 0
        if autoload:
            self.recovered_count = self.load()

    # ---------- persistence ----------

    def load(self) -> int:
        """Reloads the previous session. Returns how many points came back."""
        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return 0

        pts = []
        for raw in data.get("points", []):
            try:
                pts.append(GCPPoint.from_dict(raw))
            except (TypeError, ValueError, KeyError):
                continue  # skip a corrupt record rather than lose the rest
        self.points = pts
        self.next_index = int(data.get("next_index", len(pts) + 1))
        return len(pts)

    def save(self) -> bool:
        """Writes the session atomically so a crash mid-write cannot corrupt it."""
        payload = {
            "version": 1,
            "next_index": self.next_index,
            "points": [p.to_dict() for p in self.points],
        }
        try:
            os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
            # Write to a temp file in the same directory, then rename over the
            # target: rename is atomic, so the session file is never half-written.
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.session_path), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.session_path)
            except Exception:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise
            self.last_error = None
            return True
        except OSError as e:
            self.last_error = str(e)
            return False

    # ---------- mutations (each writes through) ----------

    def add_point(self, point: GCPPoint):
        self.points.append(point)
        self.next_index += 1
        self.save()

    def remove_point(self, index: int) -> bool:
        if 0 <= index < len(self.points):
            self.points.pop(index)
            self.save()
            return True
        return False

    def clear_all(self):
        self.points.clear()
        self.next_index = 1
        self.save()

    # ---------- queries ----------

    def get_next_point_id(self) -> str:
        """Auto-generates next Point ID (e.g. GCP001, GCP002)."""
        return f"GCP{self.next_index:03d}"

    def get_points(self) -> List[GCPPoint]:
        return list(self.points)

from typing import List, Optional
from .averaging import GCPPoint

class GCPLogger:
    """Manages logged GCP points in memory."""

    def __init__(self):
        self.points: List[GCPPoint] = []
        self.next_index: int = 1

    def add_point(self, point: GCPPoint):
        self.points.append(point)
        self.next_index += 1

    def remove_point(self, index: int) -> bool:
        if 0 <= index < len(self.points):
            self.points.pop(index)
            return True
        return False

    def clear_all(self):
        self.points.clear()
        self.next_index = 1

    def get_next_point_id(self) -> str:
        """Auto-generates next Point ID (e.g. GCP001, GCP002)."""
        return f"GCP{self.next_index:03d}"

    def get_points(self) -> List[GCPPoint]:
        return list(self.points)

import csv
from typing import List
from gcp.averaging import GCPPoint

CSV_HEADER = [
    "Point",
    "Latitude",
    "Longitude",
    "Height",
    "HorizontalAccuracy",
    "VerticalAccuracy",
    "Fix",
    "Satellites",
    "Time"
]

def export_to_csv(file_path: str, points: List[GCPPoint]) -> bool:
    """Exports list of GCPPoint objects to a Pix4D-compatible CSV file."""
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            for p in points:
                writer.writerow(p.to_csv_row())
        return True
    except Exception as e:
        print(f"CSV Export Error: {e}")
        return False

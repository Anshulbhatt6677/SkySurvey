import csv
from typing import List
from gcp.averaging import GCPPoint

# Height is WGS84 ellipsoidal, as reported by the receiver, with the antenna
# height already subtracted so it refers to the ground mark. It is NOT
# orthometric/MSL - applying a geoid model is a separate step.
CSV_HEADER = [
    "Point",
    "Latitude",
    "Longitude",
    "EllipsoidalHeight_WGS84",
    "AntennaHeight",
    "RawAntennaHeight",
    "HorizontalAccuracy",
    "VerticalAccuracy",
    "Fix",
    "QualityOverride",
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

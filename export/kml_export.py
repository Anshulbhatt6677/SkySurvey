from typing import List
from gcp.averaging import GCPPoint

def export_to_kml(file_path: str, points: List[GCPPoint]) -> bool:
    """Exports list of GCPPoint objects to a Google Earth KML file."""
    try:
        placemarks = []
        for p in points:
            pm = f"""    <Placemark>
      <name>{p.point_id}</name>
      <description><![CDATA[
        <b>Point:</b> {p.point_id}<br/>
        <b>Fix:</b> {p.fix_status}<br/>
        <b>H. Acc:</b> {p.h_accuracy} m<br/>
        <b>V. Acc:</b> {p.v_accuracy} m<br/>
        <b>Satellites:</b> {p.satellites}<br/>
        <b>Antenna Height:</b> {p.antenna_height:.3f} m (removed)<br/>
        <b>Height datum:</b> WGS84 ellipsoidal<br/>
        <b>Time:</b> {p.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
      ]]></description>
      <Point>
        <coordinates>{p.longitude},{p.latitude},{p.height}</coordinates>
      </Point>
    </Placemark>"""
            placemarks.append(pm)

        kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>SkySurvey GCP Points</name>
    <description>Ground Control Points logged by SkySurvey v1.0</description>
{chr(10).join(placemarks)}
  </Document>
</kml>"""

        with open(file_path, mode='w', encoding='utf-8') as f:
            f.write(kml_content)
        return True
    except Exception as e:
        print(f"KML Export Error: {e}")
        return False

from dataclasses import dataclass, field
from datetime import datetime
import math
import re

@dataclass
class GNSSData:
    timestamp: datetime = field(default_factory=datetime.now)
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    fix_status: str = "No Fix"  # "No Fix", "3D Fix", "RTK Float", "RTK Fixed"
    fix_quality: int = 0
    satellites: int = 0
    pdop: float = 0.0
    hdop: float = 0.0
    vdop: float = 0.0
    h_accuracy: float = 0.0  # meters
    v_accuracy: float = 0.0  # meters
    receiver_model: str = "ZED-F9P"
    firmware: str = "HPG 1.32"

    @property
    def is_valid(self) -> bool:
        return self.fix_quality > 0 and (self.latitude != 0.0 or self.longitude != 0.0)


class NMEAParser:
    """Robust NMEA sentence parser for ZED-F9P and standard GNSS receivers."""

    FIX_MAP = {
        0: "No Fix",
        1: "3D Fix",
        2: "DGPS",
        4: "RTK Fixed",
        5: "RTK Float"
    }

    def __init__(self):
        self.current_data = GNSSData()

    @staticmethod
    def _parse_deg(val: str, dir_val: str) -> float:
        """Converts NMEA ddmm.mmmm / dddmm.mmmm format to decimal degrees."""
        if not val or not dir_val:
            return 0.0
        try:
            dot_idx = val.find('.')
            if dot_idx < 0:
                return 0.0
            deg_digits = dot_idx - 2
            degrees = float(val[:deg_digits])
            minutes = float(val[deg_digits:])
            decimal = degrees + (minutes / 60.0)
            if dir_val in ['S', 'W']:
                decimal = -decimal
            return round(decimal, 9)
        except (ValueError, IndexError):
            return 0.0

    def parse_line(self, line: str) -> GNSSData:
        """Parses a single NMEA line and updates current state."""
        line = line.strip()
        if not line.startswith('$'):
            return self.current_data

        # Strip checksum if present
        if '*' in line:
            line = line.split('*')[0]

        parts = line.split(',')
        msg_id = parts[0][1:]  # e.g., GNGGA, GPGGA, GNGST, GNGSA

        # Normalize message identifier ending
        if msg_id.endswith("GGA"):
            self._parse_gga(parts)
        elif msg_id.endswith("GST"):
            self._parse_gst(parts)
        elif msg_id.endswith("GSA"):
            self._parse_gsa(parts)
        elif msg_id.endswith("RMC"):
            self._parse_rmc(parts)

        self.current_data.timestamp = datetime.now()
        return self.current_data

    def _parse_gga(self, parts: list):
        # $GNGGA,hhmmss.ss,lat,N,lon,E,quality,numSV,HDOP,alt,M,sep,M,diffAge,diffStation*cs
        if len(parts) < 10:
            return

        lat = self._parse_deg(parts[2], parts[3])
        lon = self._parse_deg(parts[4], parts[5])
        
        try:
            quality = int(parts[6]) if parts[6] else 0
        except ValueError:
            quality = 0

        try:
            satellites = int(parts[7]) if parts[7] else 0
        except ValueError:
            satellites = 0

        try:
            hdop = float(parts[8]) if parts[8] else 0.0
        except ValueError:
            hdop = 0.0

        try:
            alt = float(parts[9]) if parts[9] else 0.0
        except ValueError:
            alt = 0.0

        if lat != 0.0 or lon != 0.0:
            self.current_data.latitude = lat
            self.current_data.longitude = lon
            self.current_data.altitude = alt

        self.current_data.fix_quality = quality
        self.current_data.fix_status = self.FIX_MAP.get(quality, "3D Fix" if quality > 0 else "No Fix")
        self.current_data.satellites = satellites
        self.current_data.hdop = hdop

        # Fallback accuracy calculation if GST sentence is not emitted
        if self.current_data.h_accuracy == 0.0:
            if quality == 4: # RTK Fixed
                self.current_data.h_accuracy = 0.012
                self.current_data.v_accuracy = 0.022
            elif quality == 5: # RTK Float
                self.current_data.h_accuracy = 0.150
                self.current_data.v_accuracy = 0.280
            elif quality in [1, 2]: # Standard 3D Fix / DGPS
                self.current_data.h_accuracy = round(max(0.8, hdop * 1.2), 3)
                self.current_data.v_accuracy = round(max(1.2, hdop * 2.0), 3)

    def _parse_gst(self, parts: list):
        # $GNGST,hhmmss.ss,rangeRms,stdMajor,stdMinor,orient,stdLat,stdLon,stdAlt*cs
        if len(parts) < 9:
            return
        try:
            std_lat = float(parts[6]) if parts[6] else 0.0
            std_lon = float(parts[7]) if parts[7] else 0.0
            std_alt = float(parts[8]) if parts[8] else 0.0

            h_acc = math.sqrt(std_lat ** 2 + std_lon ** 2)
            self.current_data.h_accuracy = round(h_acc, 3)
            self.current_data.v_accuracy = round(std_alt, 3)
        except ValueError:
            pass

    def _parse_gsa(self, parts: list):
        # $GNGSA,mode1,mode2,sat1..sat12,PDOP,HDOP,VDOP*cs
        if len(parts) >= 17:
            try:
                self.current_data.pdop = float(parts[15]) if parts[15] else self.current_data.pdop
                self.current_data.vdop = float(parts[17]) if len(parts) > 17 and parts[17] else self.current_data.vdop
            except ValueError:
                pass

    def _parse_rmc(self, parts: list):
        # $GNRMC,hhmmss.ss,status,lat,N,lon,E,spd,cog,date,mv,mvE,mode*cs
        if len(parts) >= 7 and self.current_data.latitude == 0.0:
            status = parts[2]
            if status == 'A':
                lat = self._parse_deg(parts[3], parts[4])
                lon = self._parse_deg(parts[5], parts[6])
                if lat != 0.0 or lon != 0.0:
                    self.current_data.latitude = lat
                    self.current_data.longitude = lon

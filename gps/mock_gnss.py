import random
import time
from typing import Generator

class MockGNSSGenerator:
    """Generates realistic NMEA sentences simulating a ZED-F9P RTK receiver."""

    def __init__(self, base_lat=29.938742158, base_lon=78.132583944, base_alt=287.312):
        self.base_lat = base_lat
        self.base_lon = base_lon
        self.base_alt = base_alt
        self.step_count = 0

    @staticmethod
    def _to_nmea_deg(decimal_deg: float, is_lat: bool) -> tuple[str, str]:
        """Converts decimal degrees to NMEA string format (ddmm.mmmm or dddmm.mmmm)."""
        direction = ('N' if decimal_deg >= 0 else 'S') if is_lat else ('E' if decimal_deg >= 0 else 'W')
        abs_deg = abs(decimal_deg)
        degrees = int(abs_deg)
        minutes = (abs_deg - degrees) * 60.0

        if is_lat:
            deg_str = f"{degrees:02d}{minutes:07.4f}"
        else:
            deg_str = f"{degrees:03d}{minutes:07.4f}"

        return deg_str, direction

    @staticmethod
    def _add_checksum(nmea_str: str) -> str:
        """Appends NMEA 8-bit XOR checksum."""
        cs = 0
        for char in nmea_str[1:]:
            cs ^= ord(char)
        return f"{nmea_str}*{cs:02X}\r\n"

    def generate_sentences(self) -> Generator[str, None, None]:
        """Yields a batch of GNGGA, GNGST, and GNGSA sentences."""
        self.step_count += 1
        now = time.strftime("%H%M%S.00", time.gmtime())

        # Simulate walking to new GCP location every 25 cycles (~25 seconds)
        waypoint_offset = (self.step_count // 25) * 0.0001500  # ~15 meters shift per waypoint

        # Simulate small GPS noise / jitter around current waypoint
        noise_lat = random.uniform(-0.0000002, 0.0000002)
        noise_lon = random.uniform(-0.0000002, 0.0000002)
        noise_alt = random.uniform(-0.005, 0.005)

        current_lat = self.base_lat + waypoint_offset + noise_lat
        current_lon = self.base_lon + waypoint_offset + noise_lon
        current_alt = self.base_alt + (waypoint_offset * 10) + noise_alt

        # Simulate RTK state transitions (starts RTK Float for first 3 cycles, then solid RTK Fixed)
        if self.step_count <= 3:
            quality = 5  # RTK Float
            h_acc = random.uniform(0.08, 0.15)
            v_acc = random.uniform(0.12, 0.25)
            sats = random.randint(18, 22)
            pdop = round(random.uniform(1.2, 1.6), 1)
        else:
            quality = 4  # RTK Fixed
            h_acc = random.uniform(0.008, 0.015)
            v_acc = random.uniform(0.015, 0.025)
            sats = random.randint(24, 28)
            pdop = round(random.uniform(0.7, 0.9), 1)

        lat_str, lat_dir = self._to_nmea_deg(current_lat, is_lat=True)
        lon_str, lon_dir = self._to_nmea_deg(current_lon, is_lat=False)

        # 1. GNGGA
        gga_raw = f"$GNGGA,{now},{lat_str},{lat_dir},{lon_str},{lon_dir},{quality},{sats:02d},{pdop:.1f},{current_alt:.3f},M,0.0,M,1.0,0000"
        yield self._add_checksum(gga_raw)

        # 2. GNGST
        std_lat = h_acc / 1.414
        std_lon = h_acc / 1.414
        std_alt = v_acc
        gst_raw = f"$GNGST,{now},0.010,0.008,0.005,0.0,{std_lat:.3f},{std_lon:.3f},{std_alt:.3f}"
        yield self._add_checksum(gst_raw)

        # 3. GNGSA
        gsa_raw = f"$GNGSA,A,3,01,02,03,04,05,06,07,08,09,10,11,12,{pdop:.1f},0.8,{pdop:.1f}"
        yield self._add_checksum(gsa_raw)

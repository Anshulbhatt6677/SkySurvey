from gps.nmea_parser import NMEAParser
from gps.mock_gnss import MockGNSSGenerator
from gcp.averaging import GCPAverager, GCPPoint
from gcp.logger import GCPLogger
import tempfile, os
from export.csv_export import export_to_csv
from export.kml_export import export_to_kml

print("=== 1. Testing Mock GNSS & NMEA Parser ===")
gen = MockGNSSGenerator()
parser = NMEAParser()

for i, line in enumerate(gen.generate_sentences()):
    data = parser.parse_line(line)
    print(f"Sentence {i+1}: Lat={data.latitude}, Lon={data.longitude}, Alt={data.altitude}, Status={data.fix_status}, H.Acc={data.h_accuracy}m, V.Acc={data.v_accuracy}m, Sats={data.satellites}")

print("\n=== 2. Testing GCP Averaging Buffer ===")
averager = GCPAverager()
averager.start("GCP001", duration_sec=1)
for line in gen.generate_sentences():
    data = parser.parse_line(line)
    averager.add_sample(data)

averaged_point = averager.compute_average()
print("Averaged Point:", averaged_point)

print("\n=== 3. Testing GCP Logger & Next ID ===")
# Isolated session file: tests must never write into real field data.
logger = GCPLogger(session_path=os.path.join(tempfile.mkdtemp(), 'test_session.json'))
logger.add_point(averaged_point)
print("Points in Logger:", len(logger.get_points()))
print("Next Point ID:", logger.get_next_point_id())

print("\n=== 4. Testing Export Modules ===")
csv_ok = export_to_csv("test_output.csv", logger.get_points())
kml_ok = export_to_kml("test_output.kml", logger.get_points())
print(f"CSV Export: {csv_ok}, KML Export: {kml_ok}")

with open("test_output.csv", "r") as f:
    print("\nGenerated CSV Contents:")
    print(f.read())

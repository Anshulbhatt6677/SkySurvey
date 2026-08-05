import time
from PySide6.QtCore import QThread, Signal
import serial
import serial.tools.list_ports

from .nmea_parser import NMEAParser, GNSSData
from .mock_gnss import MockGNSSGenerator


MOCK_PORT_NAME = "Demo / Simulated ZED-F9P"


class SerialReaderThread(QThread):
    """Background worker thread for reading serial NMEA stream or simulated stream."""

    gnss_updated = Signal(object)        # Emits GNSSData
    connection_changed = Signal(bool, str) # Emits (is_connected, port_name)
    error_occurred = Signal(str)         # Emits error message

    def __init__(self, port: str = MOCK_PORT_NAME, baudrate: int = 38400, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.parser = NMEAParser()

    @staticmethod
    def get_available_ports() -> list[str]:
        """Scans system for available serial ports, filtering clutter and prioritizing USB GNSS ports."""
        import glob
        ports = [MOCK_PORT_NAME]
        usb_ports = []
        other_ports = []

        # Direct filesystem scan for USB / ACM serial devices (Linux / macOS)
        for pattern in ['/dev/ttyACM*', '/dev/ttyUSB*', '/dev/tty.usbmodem*', '/dev/tty.usbserial*']:
            for dev in glob.glob(pattern):
                if dev not in usb_ports:
                    usb_ports.append(dev)

        # PySerial list_ports scan (Windows COM ports & general serial ports)
        try:
            detected = serial.tools.list_ports.comports()
            for p in detected:
                dev = p.device
                if any(prefix in dev for prefix in ['ttyACM', 'ttyUSB', 'COM', 'usbmodem', 'usbserial']):
                    if dev not in usb_ports:
                        usb_ports.append(dev)
                elif not dev.startswith('/dev/ttyS'):
                    if dev not in other_ports:
                        other_ports.append(dev)
        except Exception:
            pass

        return ports + sorted(usb_ports) + sorted(other_ports)

    def run(self):
        self.running = True
        
        if MOCK_PORT_NAME in self.port:
            self._run_mock_loop()
        else:
            self._run_serial_loop()

    def stop(self):
        self.running = False
        self.wait(1000)

    def _run_mock_loop(self):
        mock_gen = MockGNSSGenerator()
        self.connection_changed.emit(True, MOCK_PORT_NAME)

        while self.running:
            for line in mock_gen.generate_sentences():
                gnss_data = self.parser.parse_line(line)
                self.gnss_updated.emit(gnss_data)
            time.sleep(1.0)

        self.connection_changed.emit(False, MOCK_PORT_NAME)

    def _run_serial_loop(self):
        ser = None
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
            self.connection_changed.emit(True, self.port)

            while self.running:
                if ser.in_waiting:
                    line = ser.readline().decode('ascii', errors='ignore')
                    if line:
                        gnss_data = self.parser.parse_line(line)
                        self.gnss_updated.emit(gnss_data)
                else:
                    time.sleep(0.05)

        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial Error: {e}")
            self.connection_changed.emit(False, self.port)
        except Exception as e:
            self.error_occurred.emit(f"Unexpected Error: {e}")
            self.connection_changed.emit(False, self.port)
        finally:
            if ser and ser.is_open:
                ser.close()
            self.connection_changed.emit(False, self.port)

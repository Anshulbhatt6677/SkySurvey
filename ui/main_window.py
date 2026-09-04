from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QMessageBox, QStatusBar, QScrollArea
)
from PySide6.QtCore import Qt, QSettings

from gps.serial_reader import SerialReaderThread
from gps.ntrip_client import NtripClientThread
from gcp.logger import GCPLogger, GCPPoint
from ui.styles import DARK_STYLESHEET
from ui.widgets import (
    ConnectionCardWidget,
    NtripCardWidget,
    StatusCardWidget,
    CoordinatesCardWidget,
    CaptureCardWidget,
    GCPTableWidget
)


class MainWindow(QMainWindow):
    """Main Application Window for SkySurvey v1.0."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SkySurvey v1.0 — GNSS GCP Mapping & Surveying")
        self.resize(1050, 620)
        self.setMinimumSize(850, 480)

        # Apply Modern Dark Theme
        self.setStyleSheet(DARK_STYLESHEET)

        # Core Data Structures & Threads
        self.logger = GCPLogger()
        self.serial_thread: SerialReaderThread = None
        self.ntrip_thread: NtripClientThread = None

        # Build GUI Layout
        self._init_ui()
        self._wire_signals()
        self._load_settings()
        self._report_recovery()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top Header Banner
        header_banner = QFrame()
        header_banner.setObjectName("cardFrame")
        header_banner.setStyleSheet("background-color: #1E293B; border-color: #38BDF8;")
        banner_layout = QHBoxLayout(header_banner)
        banner_layout.setContentsMargins(12, 6, 12, 6)

        lbl_app_title = QLabel("🛰️ SkySurvey v1.0")
        lbl_app_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #38BDF8;")
        
        lbl_subtitle = QLabel("RTK GNSS Field GCP Logger | ZED-F9P & Pix4D Ready")
        lbl_subtitle.setStyleSheet("font-size: 11px; font-weight: 600; color: #94A3B8;")

        banner_layout.addWidget(lbl_app_title)
        banner_layout.addWidget(lbl_subtitle, 1, Qt.AlignRight)
        main_layout.addWidget(header_banner)

        # Split 2-Column Body Layout
        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)

        # Left Column (Cards inside ScrollArea for smaller screens)
        left_container = QWidget()
        left_col = QVBoxLayout(left_container)
        left_col.setContentsMargins(0, 0, 4, 0)
        left_col.setSpacing(8)

        self.card_connection = ConnectionCardWidget()
        self.card_ntrip = NtripCardWidget()
        self.card_status = StatusCardWidget()
        self.card_coords = CoordinatesCardWidget()
        self.card_capture = CaptureCardWidget()

        left_col.addWidget(self.card_connection)
        left_col.addWidget(self.card_ntrip)
        left_col.addWidget(self.card_status)
        left_col.addWidget(self.card_coords)
        left_col.addWidget(self.card_capture)

        left_scroll = QScrollArea()
        left_scroll.setWidget(left_container)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFixedWidth(360)

        body_layout.addWidget(left_scroll, 0) # Fixed width left side scroll area

        # Right Column (Saved GCP Points Table & Export)
        self.card_table = GCPTableWidget(self.logger)
        body_layout.addWidget(self.card_table, 1) # Expanding right side

        main_layout.addLayout(body_layout, 1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select COM Port to start GNSS reader.")

    def _wire_signals(self):
        # Connection Card Signals
        self.card_connection.connect_requested.connect(self._start_gnss_reader)
        self.card_connection.disconnect_requested.connect(self._stop_gnss_reader)

        # NTRIP Correction Signals
        self.card_ntrip.connect_requested.connect(self._start_ntrip)
        self.card_ntrip.disconnect_requested.connect(self._stop_ntrip)

        # Capture Card Signals
        self.card_capture.gcp_saved.connect(self._on_gcp_saved)

    def _start_gnss_reader(self, port: str, baudrate: int):
        if self.serial_thread and self.serial_thread.isRunning():
            self._stop_gnss_reader()

        self.serial_thread = SerialReaderThread(port=port, baudrate=baudrate)
        self.serial_thread.gnss_updated.connect(self._on_gnss_updated)
        self.serial_thread.connection_changed.connect(self._on_connection_changed)
        self.serial_thread.error_occurred.connect(self._on_serial_error)

        self.serial_thread.start()
        self.status_bar.showMessage(f"Connecting to {port} @ {baudrate} baud...")

    def _stop_gnss_reader(self):
        self._stop_ntrip()
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
        self.card_connection.set_connected_state(False)
        self.card_status.set_connection_state(False)
        self._clear_live_readings()
        self.status_bar.showMessage("Disconnected from GNSS receiver.")

    def _load_settings(self):
        """Restores caster details and antenna height from the last session."""
        st = QSettings()
        st.beginGroup("ntrip")
        data = {k: st.value(k) for k in st.childKeys()}
        st.endGroup()
        if data:
            data["remember_pw"] = str(data.get("remember_pw", "false")).lower() in ("true", "1")
            self.card_ntrip.apply_settings(data)

        height = st.value("capture/antenna_height", 0.0)
        try:
            self.card_capture.spin_antenna.setValue(float(height))
        except (TypeError, ValueError):
            pass

    def _save_settings(self):
        st = QSettings()
        st.remove("ntrip")
        data = self.card_ntrip.export_settings()
        if data:
            st.beginGroup("ntrip")
            for k, v in data.items():
                st.setValue(k, v)
            st.endGroup()
        st.setValue("capture/antenna_height", self.card_capture.spin_antenna.value())
        st.sync()

    def _report_recovery(self):
        """Tells the operator when an interrupted session was restored."""
        n = getattr(self.logger, "recovered_count", 0)
        if n:
            self.card_table.refresh_table()
            self.card_capture.set_next_point_id(self.logger.get_next_point_id())
            self.status_bar.showMessage(
                f"Recovered {n} GCP{'s' if n != 1 else ''} from the previous session "
                f"({self.logger.session_path})"
            )

    def closeEvent(self, event):
        self._save_settings()
        self._stop_ntrip()
        self._stop_gnss_reader()
        super().closeEvent(event)

    def _start_ntrip(self, host: str, port: int, mountpoint: str, user: str, password: str):
        if not (self.serial_thread and self.serial_thread.isRunning()):
            QMessageBox.warning(self, "Receiver Not Connected",
                                "Connect to the GNSS receiver before starting corrections.\n\n"
                                "RTCM data has to be written to the receiver, so the serial "
                                "connection must be open first.")
            return

        self._stop_ntrip()

        self.ntrip_thread = NtripClientThread(host, port, mountpoint, user, password)
        self.ntrip_thread.rtcm_received.connect(self._on_rtcm_received)
        self.ntrip_thread.status_changed.connect(self._on_ntrip_status)
        self.ntrip_thread.error_occurred.connect(self._on_ntrip_error)
        self.ntrip_thread.stats_updated.connect(self.card_ntrip.update_stats)

        # VRS/network mountpoints only send corrections once they know our position.
        self.serial_thread.gga_available.connect(self.ntrip_thread.set_gga)

        self.ntrip_thread.start()
        self.card_ntrip.set_streaming_state(True)
        self.card_ntrip.set_stream_status(False, f"Connecting to {mountpoint}…")
        self.status_bar.showMessage(f"NTRIP: connecting to {host}:{port}/{mountpoint}…")

    def _stop_ntrip(self):
        if self.ntrip_thread:
            try:
                self.serial_thread.gga_available.disconnect(self.ntrip_thread.set_gga)
            except (RuntimeError, TypeError, AttributeError):
                pass
            self.ntrip_thread.stop()
            self.ntrip_thread = None
        self.card_ntrip.reset()

    def _on_rtcm_received(self, data: bytes):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.write_rtcm(data)

    def _on_ntrip_status(self, streaming: bool, message: str):
        self.card_ntrip.set_stream_status(streaming, message)
        if streaming:
            self.status_bar.showMessage(f"NTRIP: {message} | RTCM flowing to receiver")

    def _on_ntrip_error(self, err_msg: str):
        self.card_ntrip.set_streaming_state(False)
        self.card_ntrip.set_stream_status(False, err_msg)
        self.status_bar.showMessage(f"NTRIP error: {err_msg}")

    def _clear_live_readings(self):
        """Wipes the live panels so a stale fix is never shown as current."""
        self.card_status.reset()
        self.card_coords.reset()
        self.card_capture.reset()

    def _on_gnss_updated(self, gnss_data):
        self.card_status.update_gnss(gnss_data)
        self.card_coords.update_gnss(gnss_data)
        self.card_capture.update_gnss(gnss_data)

    def _on_connection_changed(self, is_connected: bool, port_name: str):
        self.card_connection.set_connected_state(is_connected, port_name)
        self.card_status.set_connection_state(is_connected)
        if is_connected:
            self.status_bar.showMessage(f"Connected to {port_name} | Streaming NMEA data...")
        else:
            self._clear_live_readings()
            self.status_bar.showMessage("Disconnected.")

    def _on_serial_error(self, err_msg: str):
        QMessageBox.critical(self, "GNSS Serial Error", err_msg)
        self._stop_gnss_reader()

    def _on_gcp_saved(self, point: GCPPoint):
        self.logger.add_point(point)
        if self.logger.last_error:
            QMessageBox.warning(
                self, "Autosave Failed",
                f"{point.point_id} is in memory but could not be written to disk:\n\n"
                f"{self.logger.last_error}\n\nExport to CSV now — an app or power "
                f"failure would lose this session."
            )
        self.card_table.refresh_table()
        
        # Auto increment next Point ID
        next_id = self.logger.get_next_point_id()
        self.card_capture.set_next_point_id(next_id)
        self.status_bar.showMessage(f"✔ Saved Point {point.point_id} to log.")

    def closeEvent(self, event):
        self._stop_gnss_reader()
        event.accept()

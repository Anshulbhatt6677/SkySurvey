from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QProgressBar
)
from PySide6.QtCore import Signal, QTimer
from gcp.averaging import GCPAverager, GCPPoint
from gps.nmea_parser import GNSSData


class CaptureCardWidget(QFrame):
    """Widget for GCP point name entry, sample averaging, and countdown progress bar."""

    gcp_saved = Signal(GCPPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.averager = GCPAverager()
        self.current_gnss: GNSSData = None
        self._init_ui()

        # Timer for updating countdown progress bar
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(100)
        self.progress_timer.timeout.connect(self._update_progress)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("5. GCP Capture")
        header.setObjectName("cardHeader")
        layout.addWidget(header)

        # Point ID Input
        row1 = QHBoxLayout()
        lbl_pt = QLabel("Current Point:")
        lbl_pt.setObjectName("metricTitle")
        self.input_point_id = QLineEdit("GCP001")
        row1.addWidget(lbl_pt)
        row1.addWidget(self.input_point_id, 1)
        layout.addLayout(row1)

        # Average Time Combobox
        row2 = QHBoxLayout()
        lbl_time = QLabel("Average Time:")
        lbl_time.setObjectName("metricTitle")
        self.combo_time = QComboBox()
        self.combo_time.addItems(["5 seconds", "10 seconds", "15 seconds", "30 seconds", "60 seconds"])
        self.combo_time.setCurrentText("15 seconds")
        row2.addWidget(lbl_time)
        row2.addWidget(self.combo_time, 1)
        layout.addLayout(row2)

        # Save GCP Button
        self.btn_save = QPushButton("[ Save GCP ]")
        self.btn_save.setObjectName("saveButton")
        self.btn_save.clicked.connect(self._start_save_gcp)
        layout.addWidget(self.btn_save)

        # Progress Bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready to capture")
        layout.addWidget(self.progress_bar)

    def update_gnss(self, data: GNSSData):
        self.current_gnss = data
        if self.averager.active and data:
            done = self.averager.add_sample(data)
            if done:
                self._finish_averaging()

    def set_next_point_id(self, point_id: str):
        self.input_point_id.setText(point_id)

    def _get_selected_seconds(self) -> int:
        txt = self.combo_time.currentText()
        try:
            return int(txt.split()[0])
        except (ValueError, IndexError):
            return 15

    def _start_save_gcp(self):
        if not self.current_gnss or not self.current_gnss.is_valid:
            self.progress_bar.setFormat("❌ Cannot Save: No valid GNSS Fix!")
            return

        point_id = self.input_point_id.text().strip() or "GCP001"
        sec = self._get_selected_seconds()

        self.averager.start(point_id, sec)
        self.btn_save.setEnabled(False)
        self.input_point_id.setEnabled(False)
        self.combo_time.setEnabled(False)

        self.progress_timer.start()

    def _update_progress(self):
        if not self.averager.active:
            return

        pct = self.averager.get_progress_percent()
        rem = self.averager.get_remaining_seconds()

        self.progress_bar.setValue(int(pct))
        self.progress_bar.setFormat(f"Averaging... {rem}s remaining ({int(pct)}%)")

    def _finish_averaging(self):
        self.progress_timer.stop()
        self.progress_bar.setValue(100)
        
        point = self.averager.compute_average()
        if point:
            self.progress_bar.setFormat(f"✔ Saved {point.point_id} ({point.sample_count} samples averaged)")
            self.gcp_saved.emit(point)
        else:
            self.progress_bar.setFormat("❌ Averaging Failed (No samples)")

        self.btn_save.setEnabled(True)
        self.input_point_id.setEnabled(True)
        self.combo_time.setEnabled(True)

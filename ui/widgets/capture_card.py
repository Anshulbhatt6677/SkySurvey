from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QProgressBar, QCheckBox, QDoubleSpinBox
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

        header = QLabel("6. GCP Capture")
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

        # Antenna / pole height above the ground mark
        row3 = QHBoxLayout()
        lbl_ant = QLabel("Antenna Height:")
        lbl_ant.setObjectName("metricTitle")
        self.spin_antenna = QDoubleSpinBox()
        self.spin_antenna.setRange(0.0, 10.0)
        self.spin_antenna.setDecimals(3)
        self.spin_antenna.setSingleStep(0.01)
        self.spin_antenna.setSuffix(" m")
        self.spin_antenna.setToolTip(
            "Vertical distance from the ground mark up to the antenna phase centre.\n"
            "Subtracted from the recorded height so the point refers to the mark."
        )
        row3.addWidget(lbl_ant)
        row3.addWidget(self.spin_antenna, 1)
        layout.addLayout(row3)

        # Quality gate
        self.chk_allow_non_rtk = QCheckBox("Allow capture below RTK Fixed")
        self.chk_allow_non_rtk.setToolTip(
            "GCPs are only survey-grade at RTK Fixed (centimetre).\n"
            "Ticking this permits lower-quality points; they are flagged in the\n"
            "table and exported with QualityOverride=YES."
        )
        layout.addWidget(self.chk_allow_non_rtk)

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

        # A GCP is only survey-grade at RTK Fixed. Anything less is metre-level
        # and would silently poison the photogrammetry, so it takes a deliberate
        # opt-in and is marked on the point itself.
        if self.current_gnss.fix_status != "RTK Fixed" and not self.chk_allow_non_rtk.isChecked():
            self.progress_bar.setFormat(
                f"❌ Need RTK Fixed (have {self.current_gnss.fix_status})"
            )
            return

        point_id = self.input_point_id.text().strip() or "GCP001"
        sec = self._get_selected_seconds()

        self.averager.start(point_id, sec, antenna_height=self.spin_antenna.value())
        self._set_controls_enabled(False)

        self.progress_timer.start()

    def _update_progress(self):
        if not self.averager.active:
            return

        # The stream can die mid-capture (disconnect, cable pull, receiver power loss).
        # Averaging only completes inside add_sample(), so without this the capture
        # would stay active forever and the controls would never re-enable.
        if self.averager.is_stalled():
            self._abort_capture("❌ Capture aborted: GNSS stream lost")
            return

        pct = self.averager.get_progress_percent()
        rem = self.averager.get_remaining_seconds()

        self.progress_bar.setValue(int(pct))
        self.progress_bar.setFormat(f"Averaging... {rem}s remaining ({int(pct)}%)")

    def _abort_capture(self, message: str):
        """Discards an in-flight capture and restores the controls."""
        self.progress_timer.stop()
        self.averager.cancel()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(message)
        self._set_controls_enabled(True)

    def reset(self):
        """Drops the last fix and any running capture when the stream goes away."""
        self.current_gnss = None
        if self.averager.active:
            self._abort_capture("❌ Capture aborted: disconnected")
        else:
            self.progress_timer.stop()
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Ready to capture")
            self._set_controls_enabled(True)

    def _set_controls_enabled(self, enabled: bool):
        self.btn_save.setEnabled(enabled)
        self.input_point_id.setEnabled(enabled)
        self.combo_time.setEnabled(enabled)
        self.spin_antenna.setEnabled(enabled)
        self.chk_allow_non_rtk.setEnabled(enabled)

    def _finish_averaging(self):
        self.progress_timer.stop()
        self.progress_bar.setValue(100)
        
        point = self.averager.compute_average()
        if point:
            point.quality_override = point.fix_status != "RTK Fixed"
            flag = "  ⚠ below RTK Fixed" if point.quality_override else ""
            self.progress_bar.setFormat(
                f"✔ Saved {point.point_id} ({point.sample_count} samples){flag}"
            )
            self.gcp_saved.emit(point)
        else:
            self.progress_bar.setFormat("❌ Averaging Failed (No samples)")

        self._set_controls_enabled(True)

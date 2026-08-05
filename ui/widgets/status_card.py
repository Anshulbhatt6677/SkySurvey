from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
)
from gps.nmea_parser import GNSSData


class StatusCardWidget(QFrame):
    """Widget displaying receiver information, connection state, and RTK fix status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QLabel("2. Receiver Information")
        header.setObjectName("cardHeader")
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(8)

        # Connection Status
        grid.addWidget(self._create_title_lbl("Status:"), 0, 0)
        self.lbl_conn_status = QLabel("Disconnected ✖")
        self.lbl_conn_status.setStyleSheet("color: #94A3B8; font-weight: 700;")
        grid.addWidget(self.lbl_conn_status, 0, 1)

        # Receiver Model
        grid.addWidget(self._create_title_lbl("Model:"), 1, 0)
        self.lbl_model = QLabel("ZED-F9P")
        self.lbl_model.setStyleSheet("color: #F8FAFC; font-weight: 600;")
        grid.addWidget(self.lbl_model, 1, 1)

        # Firmware
        grid.addWidget(self._create_title_lbl("Firmware:"), 2, 0)
        self.lbl_fw = QLabel("HPG 1.32")
        self.lbl_fw.setStyleSheet("color: #F8FAFC; font-weight: 600;")
        grid.addWidget(self.lbl_fw, 2, 1)

        layout.addLayout(grid)

        # RTK Status Section
        lbl_rtk = QLabel("RTK Status:")
        lbl_rtk.setObjectName("metricTitle")
        layout.addWidget(lbl_rtk)

        self.lbl_badge = QLabel("○ No Fix")
        self.lbl_badge.setObjectName("rtkBadgeNoFix")
        layout.addWidget(self.lbl_badge)

    @staticmethod
    def _create_title_lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("metricTitle")
        return lbl

    def update_gnss(self, data: GNSSData):
        if not data:
            return
        
        status = data.fix_status
        if status == "RTK Fixed":
            self.lbl_badge.setText("🟢 RTK Fixed")
            self.lbl_badge.setObjectName("rtkBadgeFixed")
        elif status == "RTK Float":
            self.lbl_badge.setText("🟢 RTK Float")
            self.lbl_badge.setObjectName("rtkBadgeFloat")
        elif status in ["3D Fix", "DGPS"]:
            self.lbl_badge.setText(f"🟡 {status}")
            self.lbl_badge.setObjectName("rtkBadge3D")
        else:
            self.lbl_badge.setText("🔴 No Fix")
            self.lbl_badge.setObjectName("rtkBadgeNoFix")

        # Re-apply CSS selector stylesheet
        self.lbl_badge.setStyle(self.lbl_badge.style())

    def set_connection_state(self, connected: bool):
        if connected:
            self.lbl_conn_status.setText("Connected ✔")
            self.lbl_conn_status.setStyleSheet("color: #10B981; font-weight: 700;")
        else:
            self.lbl_conn_status.setText("Disconnected ✖")
            self.lbl_conn_status.setStyleSheet("color: #94A3B8; font-weight: 700;")
            self.lbl_badge.setText("○ No Fix")
            self.lbl_badge.setObjectName("rtkBadgeNoFix")
            self.lbl_badge.setStyle(self.lbl_badge.style())

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
)
from gps.nmea_parser import GNSSData


class CoordinatesCardWidget(QFrame):
    """Widget displaying live GNSS coordinates and accuracy metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        header = QLabel("4. Live Coordinates & 5. Accuracy")
        header.setObjectName("cardHeader")
        layout.addWidget(header)

        # Coordinate Column / Box
        coord_grid = QGridLayout()
        coord_grid.setVerticalSpacing(4)

        coord_grid.addWidget(self._create_title_lbl("Latitude"), 0, 0)
        self.lbl_lat = QLabel("0.000000000°")
        self.lbl_lat.setObjectName("coordValue")
        coord_grid.addWidget(self.lbl_lat, 1, 0)

        coord_grid.addWidget(self._create_title_lbl("Longitude"), 2, 0)
        self.lbl_lon = QLabel("0.000000000°")
        self.lbl_lon.setObjectName("coordValue")
        coord_grid.addWidget(self.lbl_lon, 3, 0)

        coord_grid.addWidget(self._create_title_lbl("Height"), 4, 0)
        self.lbl_alt = QLabel("0.000 m")
        self.lbl_alt.setObjectName("coordValue")
        coord_grid.addWidget(self.lbl_alt, 5, 0)

        layout.addLayout(coord_grid)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("border-color: #334155;")
        layout.addWidget(divider)

        # Accuracy Grid (2x2)
        acc_grid = QGridLayout()
        acc_grid.setHorizontalSpacing(20)
        acc_grid.setVerticalSpacing(8)

        # Horiz Acc
        acc_grid.addWidget(self._create_title_lbl("H. Accuracy"), 0, 0)
        self.lbl_h_acc = QLabel("0.000 m")
        self.lbl_h_acc.setObjectName("metricValue")
        acc_grid.addWidget(self.lbl_h_acc, 1, 0)

        # Vert Acc
        acc_grid.addWidget(self._create_title_lbl("V. Accuracy"), 0, 1)
        self.lbl_v_acc = QLabel("0.000 m")
        self.lbl_v_acc.setObjectName("metricValue")
        acc_grid.addWidget(self.lbl_v_acc, 1, 1)

        # PDOP
        acc_grid.addWidget(self._create_title_lbl("PDOP"), 2, 0)
        self.lbl_pdop = QLabel("0.0")
        self.lbl_pdop.setObjectName("metricValue")
        acc_grid.addWidget(self.lbl_pdop, 3, 0)

        # Satellites
        acc_grid.addWidget(self._create_title_lbl("Satellites"), 2, 1)
        self.lbl_sats = QLabel("0")
        self.lbl_sats.setObjectName("metricValue")
        acc_grid.addWidget(self.lbl_sats, 3, 1)

        layout.addLayout(acc_grid)

    @staticmethod
    def _create_title_lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("metricTitle")
        return lbl

    def reset(self):
        """Blanks every reading so stale values cannot be mistaken for live ones."""
        self.lbl_lat.setText("—")
        self.lbl_lon.setText("—")
        self.lbl_alt.setText("—")
        self.lbl_h_acc.setText("—")
        self.lbl_v_acc.setText("—")
        self.lbl_pdop.setText("—")
        self.lbl_sats.setText("—")

    def update_gnss(self, data: GNSSData):
        if not data:
            return
        
        self.lbl_lat.setText(f"{data.latitude:.9f}°")
        self.lbl_lon.setText(f"{data.longitude:.9f}°")
        self.lbl_alt.setText(f"{data.altitude:.3f} m")

        self.lbl_h_acc.setText(f"{data.h_accuracy:.3f} m")
        self.lbl_v_acc.setText(f"{data.v_accuracy:.3f} m")
        self.lbl_pdop.setText(f"{data.pdop:.1f}")
        self.lbl_sats.setText(str(data.satellites))

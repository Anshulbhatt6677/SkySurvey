from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
)
from PySide6.QtCore import Signal
from gps.serial_reader import SerialReaderThread


class ConnectionCardWidget(QFrame):
    """Widget for selecting COM port, baud rate, and toggling serial connection."""

    connect_requested = Signal(str, int)  # (port, baudrate)
    disconnect_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.is_connected = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("1. GNSS Connection")
        header.setObjectName("cardHeader")
        layout.addWidget(header)

        # Form Row 1: COM Port
        row1 = QHBoxLayout()
        lbl_port = QLabel("COM Port:")
        lbl_port.setObjectName("metricTitle")
        self.combo_port = QComboBox()
        self.refresh_ports()
        row1.addWidget(lbl_port)
        row1.addWidget(self.combo_port, 1)
        layout.addLayout(row1)

        # Form Row 2: Baud Rate
        row2 = QHBoxLayout()
        lbl_baud = QLabel("Baud Rate:")
        lbl_baud.setObjectName("metricTitle")
        self.combo_baud = QComboBox()
        self.combo_baud.addItems(["38400", "9600", "115200", "57600", "230400"])
        self.combo_baud.setCurrentText("38400")
        row2.addWidget(lbl_baud)
        row2.addWidget(self.combo_baud, 1)
        layout.addLayout(row2)

        # Connect / Refresh Buttons
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setToolTip("Rescan system serial ports")
        self.btn_refresh.clicked.connect(self.refresh_ports)

        self.btn_connect = QPushButton("[ Connect ]")
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_connect, 1)
        layout.addLayout(btn_layout)

    def refresh_ports(self):
        current = self.combo_port.currentText()
        self.combo_port.clear()
        ports = SerialReaderThread.get_available_ports()
        self.combo_port.addItems(ports)
        
        if current and current in ports:
            self.combo_port.setCurrentText(current)
        else:
            # Auto-select real USB hardware port if detected
            for p in ports:
                if any(k in p for k in ['ttyACM', 'ttyUSB', 'COM']):
                    self.combo_port.setCurrentText(p)
                    break

    def _on_connect_clicked(self):
        if not self.is_connected:
            port = self.combo_port.currentText()
            baud = int(self.combo_baud.currentText())
            self.connect_requested.emit(port, baud)
        else:
            self.disconnect_requested.emit()

    def set_connected_state(self, connected: bool, port_name: str = ""):
        self.is_connected = connected
        if connected:
            self.btn_connect.setText("[ Disconnect ]")
            self.btn_connect.setStyleSheet("background-color: #EF4444; color: white;")
            self.combo_port.setEnabled(False)
            self.combo_baud.setEnabled(False)
            self.btn_refresh.setEnabled(False)
        else:
            self.btn_connect.setText("[ Connect ]")
            self.btn_connect.setStyleSheet("")
            self.combo_port.setEnabled(True)
            self.combo_baud.setEnabled(True)
            self.btn_refresh.setEnabled(True)

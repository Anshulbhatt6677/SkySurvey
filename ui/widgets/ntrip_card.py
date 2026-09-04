from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox
)
from PySide6.QtCore import Signal, Qt

from gps.ntrip_client import fetch_sourcetable, DEFAULT_NTRIP_PORT


class NtripCardWidget(QFrame):
    """Widget for entering NTRIP caster details and toggling the correction stream."""

    connect_requested = Signal(str, int, str, str, str)  # host, port, mountpoint, user, pass
    disconnect_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.is_streaming = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QLabel("2. RTK Corrections (NTRIP)")
        header.setObjectName("cardHeader")
        layout.addWidget(header)

        # Caster host + port
        row_host = QHBoxLayout()
        lbl_host = QLabel("Caster:")
        lbl_host.setObjectName("metricTitle")
        self.input_host = QLineEdit()
        self.input_host.setPlaceholderText("caster hostname or IP")
        self.input_port = QLineEdit(str(DEFAULT_NTRIP_PORT))
        self.input_port.setFixedWidth(58)
        self.input_port.setAlignment(Qt.AlignCenter)
        row_host.addWidget(lbl_host)
        row_host.addWidget(self.input_host, 1)
        row_host.addWidget(self.input_port)
        layout.addLayout(row_host)

        # Credentials
        row_user = QHBoxLayout()
        lbl_user = QLabel("User / Pass:")
        lbl_user.setObjectName("metricTitle")
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("username")
        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("password")
        self.input_pass.setEchoMode(QLineEdit.Password)
        row_user.addWidget(lbl_user)
        row_user.addWidget(self.input_user, 1)
        row_user.addWidget(self.input_pass, 1)
        layout.addLayout(row_user)

        # Mountpoint + sourcetable fetch
        row_mount = QHBoxLayout()
        lbl_mount = QLabel("Mountpoint:")
        lbl_mount.setObjectName("metricTitle")
        self.combo_mount = QComboBox()
        self.combo_mount.setEditable(True)
        self.btn_fetch = QPushButton("⤓ List")
        self.btn_fetch.setToolTip("Fetch the caster's sourcetable to list available mountpoints")
        self.btn_fetch.clicked.connect(self._on_fetch_clicked)
        row_mount.addWidget(lbl_mount)
        row_mount.addWidget(self.combo_mount, 1)
        row_mount.addWidget(self.btn_fetch)
        layout.addLayout(row_mount)

        # Credentials are re-typed every launch otherwise, which is painful in
        # the field; the password is opt-in because QSettings stores it as plain text.
        self.chk_remember = QCheckBox("Remember these settings")
        self.chk_remember.setChecked(True)
        self.chk_remember_pw = QCheckBox("…including password (stored unencrypted)")
        self.chk_remember_pw.setToolTip(
            "QSettings keeps this in a plain-text config file on this machine.\n"
            "Leave off on a shared or field laptop."
        )
        layout.addWidget(self.chk_remember)
        layout.addWidget(self.chk_remember_pw)

        # Connect button
        self.btn_connect = QPushButton("[ Start Corrections ]")
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.btn_connect)

        # Live stream status
        self.lbl_stream = QLabel("○ No corrections")
        self.lbl_stream.setObjectName("rtkBadgeNoFix")
        layout.addWidget(self.lbl_stream)

    # ---------- actions ----------

    def _on_fetch_clicked(self):
        host = self.input_host.text().strip()
        if not host:
            self.set_stream_status(False, "Enter a caster hostname first")
            return
        try:
            port = int(self.input_port.text().strip() or DEFAULT_NTRIP_PORT)
        except ValueError:
            self.set_stream_status(False, "Port must be a number")
            return

        self.btn_fetch.setEnabled(False)
        self.set_stream_status(False, "Fetching mountpoint list…")
        try:
            entries = fetch_sourcetable(host, port,
                                        self.input_user.text().strip(),
                                        self.input_pass.text())
            current = self.combo_mount.currentText()
            self.combo_mount.clear()
            for e in entries:
                self.combo_mount.addItem(e.mountpoint)
                self.combo_mount.setItemData(self.combo_mount.count() - 1, e.label(), Qt.ToolTipRole)
            if current:
                self.combo_mount.setCurrentText(current)
            self.set_stream_status(False, f"Found {len(entries)} mountpoints — pick one")
        except Exception as e:
            self.set_stream_status(False, f"Sourcetable failed: {e}")
        finally:
            self.btn_fetch.setEnabled(True)

    def _on_connect_clicked(self):
        if self.is_streaming:
            self.disconnect_requested.emit()
            return

        host = self.input_host.text().strip()
        mount = self.combo_mount.currentText().strip()
        if not host or not mount:
            self.set_stream_status(False, "Caster and mountpoint are required")
            return
        try:
            port = int(self.input_port.text().strip() or DEFAULT_NTRIP_PORT)
        except ValueError:
            self.set_stream_status(False, "Port must be a number")
            return

        self.connect_requested.emit(host, port, mount,
                                    self.input_user.text().strip(),
                                    self.input_pass.text())

    # ---------- state ----------

    def set_streaming_state(self, streaming: bool):
        self.is_streaming = streaming
        self.btn_connect.setText("[ Stop Corrections ]" if streaming else "[ Start Corrections ]")
        self.btn_connect.setStyleSheet("background-color: #EF4444; color: white;" if streaming else "")
        for w in (self.input_host, self.input_port, self.input_user,
                  self.input_pass, self.combo_mount, self.btn_fetch):
            w.setEnabled(not streaming)

    def set_stream_status(self, active: bool, message: str):
        self.lbl_stream.setText(("🟢 " if active else "○ ") + message)
        self.lbl_stream.setObjectName("rtkBadgeFixed" if active else "rtkBadgeNoFix")
        self.lbl_stream.setStyle(self.lbl_stream.style())

    def update_stats(self, total_bytes: int, age_sec: float):
        kb = total_bytes / 1024.0
        size = f"{kb:.1f} KB" if kb < 1024 else f"{kb/1024.0:.2f} MB"
        # Corrections older than a few seconds stop being useful for RTK.
        stale = age_sec > 5.0
        self.lbl_stream.setText(
            f"{'🟡' if stale else '🟢'} {size} received  |  age {age_sec:.0f}s"
        )
        self.lbl_stream.setObjectName("rtkBadge3D" if stale else "rtkBadgeFixed")
        self.lbl_stream.setStyle(self.lbl_stream.style())

    def reset(self):
        self.set_streaming_state(False)
        self.set_stream_status(False, "No corrections")

    # ---------- persistence ----------

    def export_settings(self) -> dict:
        """Returns the fields worth remembering between sessions."""
        if not self.chk_remember.isChecked():
            return {}
        data = {
            "host": self.input_host.text().strip(),
            "port": self.input_port.text().strip(),
            "mount": self.combo_mount.currentText().strip(),
            "user": self.input_user.text().strip(),
            "remember_pw": self.chk_remember_pw.isChecked(),
        }
        if self.chk_remember_pw.isChecked():
            data["password"] = self.input_pass.text()
        return data

    def apply_settings(self, data: dict):
        if not data:
            return
        self.input_host.setText(data.get("host", ""))
        self.input_port.setText(data.get("port", str(DEFAULT_NTRIP_PORT)) or str(DEFAULT_NTRIP_PORT))
        mount = data.get("mount", "")
        if mount:
            if self.combo_mount.findText(mount) < 0:
                self.combo_mount.addItem(mount)
            self.combo_mount.setCurrentText(mount)
        self.input_user.setText(data.get("user", ""))
        self.chk_remember_pw.setChecked(bool(data.get("remember_pw", False)))
        if data.get("password"):
            self.input_pass.setText(data["password"])

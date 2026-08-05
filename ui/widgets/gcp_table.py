from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QFileDialog, QMessageBox
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from gcp.logger import GCPLogger, GCPPoint
from export.csv_export import export_to_csv
from export.kml_export import export_to_kml


class GCPTableWidget(QFrame):
    """Widget displaying the table of logged GCPs with export options."""

    points_changed = Signal()

    def __init__(self, logger: GCPLogger, parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.logger = logger
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header & Export Bar
        top_row = QHBoxLayout()
        header = QLabel("6. Saved Points & 7. Export")
        header.setObjectName("cardHeader")
        top_row.addWidget(header, 1)

        self.btn_export_csv = QPushButton("📄 Export CSV")
        self.btn_export_csv.setObjectName("exportCsvBtn")
        self.btn_export_csv.clicked.connect(self._on_export_csv)
        top_row.addWidget(self.btn_export_csv)

        self.btn_export_kml = QPushButton("🗺️ Export KML")
        self.btn_export_kml.setObjectName("exportKmlBtn")
        self.btn_export_kml.clicked.connect(self._on_export_kml)
        top_row.addWidget(self.btn_export_kml)

        self.btn_clear = QPushButton("🗑️ Clear")
        self.btn_clear.setStyleSheet("background-color: #475569; color: white;")
        self.btn_clear.clicked.connect(self._on_clear_all)
        top_row.addWidget(self.btn_clear)

        layout.addLayout(top_row)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Point", "Latitude", "Longitude", "Height (m)",
            "H.Acc (m)", "V.Acc (m)", "Fix Status", "Sats", "Time", "Action"
        ])
        
        # Table Header Sizing
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(9, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)

    def refresh_table(self):
        self.table.setRowCount(0)
        points = self.logger.get_points()

        for row_idx, p in enumerate(points):
            self.table.insertRow(row_idx)

            # Item 0: Point
            item_pt = QTableWidgetItem(p.point_id)
            item_pt.setTextAlignment(0x0084) # Align Center
            self.table.setItem(row_idx, 0, item_pt)

            # Item 1: Latitude
            item_lat = QTableWidgetItem(f"{p.latitude:.9f}")
            self.table.setItem(row_idx, 1, item_lat)

            # Item 2: Longitude
            item_lon = QTableWidgetItem(f"{p.longitude:.9f}")
            self.table.setItem(row_idx, 2, item_lon)

            # Item 3: Height
            item_alt = QTableWidgetItem(f"{p.height:.3f}")
            self.table.setItem(row_idx, 3, item_alt)

            # Item 4: H.Acc
            item_h = QTableWidgetItem(f"{p.h_accuracy:.3f}")
            self.table.setItem(row_idx, 4, item_h)

            # Item 5: V.Acc
            item_v = QTableWidgetItem(f"{p.v_accuracy:.3f}")
            self.table.setItem(row_idx, 5, item_v)

            # Item 6: Fix Status Badge
            item_fix = QTableWidgetItem(p.fix_status)
            if p.fix_status == "RTK Fixed":
                item_fix.setForeground(QColor("#10B981"))
            elif p.fix_status == "RTK Float":
                item_fix.setForeground(QColor("#06B6D4"))
            else:
                item_fix.setForeground(QColor("#F59E0B"))
            self.table.setItem(row_idx, 6, item_fix)

            # Item 7: Satellites
            item_sat = QTableWidgetItem(str(p.satellites))
            self.table.setItem(row_idx, 7, item_sat)

            # Item 8: Time
            item_time = QTableWidgetItem(p.timestamp.strftime("%H:%M:%S"))
            self.table.setItem(row_idx, 8, item_time)

            # Item 9: Delete Button
            btn_del = QPushButton("❌")
            btn_del.setToolTip("Delete point")
            btn_del.setStyleSheet("background-color: transparent; color: #EF4444; font-weight: bold;")
            btn_del.clicked.connect(lambda _, r=row_idx: self._delete_row(r))
            self.table.setCellWidget(row_idx, 9, btn_del)

    def _delete_row(self, row_idx: int):
        self.logger.remove_point(row_idx)
        self.refresh_table()
        self.points_changed.emit()

    def _on_clear_all(self):
        if not self.logger.get_points():
            return
        reply = QMessageBox.question(
            self, "Clear All Points",
            "Are you sure you want to clear all logged GCP points?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.logger.clear_all()
            self.refresh_table()
            self.points_changed.emit()

    def _on_export_csv(self):
        points = self.logger.get_points()
        if not points:
            QMessageBox.warning(self, "Export CSV", "No GCP points to export!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Pix4D CSV File", "SkySurvey_GCPs.csv", "CSV Files (*.csv)"
        )
        if file_path:
            if export_to_csv(file_path, points):
                QMessageBox.information(self, "Export Successful", f"GCPs successfully exported to:\n{file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to write CSV file!")

    def _on_export_kml(self):
        points = self.logger.get_points()
        if not points:
            QMessageBox.warning(self, "Export KML", "No GCP points to export!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Google Earth KML File", "SkySurvey_GCPs.kml", "KML Files (*.kml)"
        )
        if file_path:
            if export_to_kml(file_path, points):
                QMessageBox.information(self, "Export Successful", f"GCPs successfully exported to:\n{file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to write KML file!")

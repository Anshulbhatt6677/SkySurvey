#!/usr/bin/env python3
"""
SkySurvey v1.0 — GNSS GCP Mapping & Surveying Application Entry Point
"""

import sys
import os

# Ensure project root directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SkySurvey")
    app.setOrganizationName("SkySurvey")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

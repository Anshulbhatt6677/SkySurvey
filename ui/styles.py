"""
SkySurvey v1.0 Modern Dark Theme Stylesheet
Tailored for survey field operations with high legibility and rich visual aesthetics.
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
}

QWidget {
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    color: #F8FAFC;
}

/* Glassmorphism / Modern Card Panels */
QFrame#cardFrame {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 8px 12px;
}

/* Headers & Labels */
QLabel#cardHeader {
    font-size: 14px;
    font-weight: 700;
    color: #38BDF8;
    letter-spacing: 0.5px;
    padding-bottom: 2px;
}

QLabel#metricTitle {
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
}

QLabel#metricValue {
    font-size: 15px;
    font-weight: 700;
    color: #F8FAFC;
    font-family: 'Monaco', 'Consolas', monospace;
}

QLabel#coordValue {
    font-size: 17px;
    font-weight: 800;
    color: #38BDF8;
    font-family: 'Monaco', 'Consolas', monospace;
}

/* Inputs & Comboboxes */
QComboBox, QLineEdit, QSpinBox {
    background-color: #0F172A;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 4px 8px;
    color: #F8FAFC;
    font-size: 12px;
    selection-background-color: #0284C7;
}

QComboBox:hover, QLineEdit:hover {
    border: 1px solid #38BDF8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Buttons */
QPushButton {
    background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%);
    background-color: #0284C7;
    border: none;
    border-radius: 6px;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 14px;
}

QPushButton:hover {
    background-color: #38BDF8;
    color: #0F172A;
}

QPushButton:pressed {
    background-color: #0369A1;
}

QPushButton#saveButton {
    background-color: #10B981;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 800;
    padding: 8px 16px;
    border-radius: 6px;
}

QPushButton#saveButton:hover {
    background-color: #34D399;
}

QPushButton#saveButton:disabled {
    background-color: #334155;
    color: #64748B;
}

QPushButton#exportCsvBtn {
    background-color: #8B5CF6;
    color: #FFFFFF;
}

QPushButton#exportCsvBtn:hover {
    background-color: #A78BFA;
}

QPushButton#exportKmlBtn {
    background-color: #06B6D4;
    color: #FFFFFF;
}

QPushButton#exportKmlBtn:hover {
    background-color: #22D3EE;
}

/* Progress Bar */
QProgressBar {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 700;
    min-height: 20px;
    max-height: 24px;
}

QProgressBar::chunk {
    background-color: #10B981;
    border-radius: 5px;
}

/* Table Widget */
QTableWidget {
    background-color: #0F172A;
    gridline-color: #334155;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #F8FAFC;
    font-size: 13px;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #1E293B;
}

QTableWidget::item:selected {
    background-color: #1E293B;
    color: #38BDF8;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    font-weight: 700;
    font-size: 12px;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #334155;
}

/* Status Badges */
QLabel#rtkBadgeFixed {
    background-color: rgba(16, 185, 129, 0.2);
    color: #10B981;
    border: 1px solid #10B981;
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 700;
}

QLabel#rtkBadgeFloat {
    background-color: rgba(6, 182, 212, 0.2);
    color: #06B6D4;
    border: 1px solid #06B6D4;
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 700;
}

QLabel#rtkBadge3D {
    background-color: rgba(245, 158, 11, 0.2);
    color: #F59E0B;
    border: 1px solid #F59E0B;
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 700;
}

QLabel#rtkBadgeNoFix {
    background-color: rgba(239, 68, 68, 0.2);
    color: #EF4444;
    border: 1px solid #EF4444;
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 700;
}
"""

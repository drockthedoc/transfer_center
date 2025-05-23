"""
Patient Information Widget for the Transfer Center GUI.

This module contains the patient information input widget used in the main application window.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PatientInfoWidget(QWidget):
    """Widget for inputting patient information."""

    data_changed = pyqtSignal()  # Signal when patient data changes

    def __init__(self, parent=None):
        """Initialize the patient information widget."""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Patient Information Group
        patient_group = QGroupBox("Patient Information")
        patient_layout = QFormLayout()
        patient_layout.setContentsMargins(5, 5, 5, 5)
        patient_layout.setVerticalSpacing(2)
        patient_layout.setHorizontalSpacing(5)

        self.patient_id_input = QLineEdit()
        self.patient_id_input.setPlaceholderText("Enter patient ID")
        self.patient_id_input.textChanged.connect(self.data_changed)

        self.clinical_data_input = QTextEdit()
        self.clinical_data_input.setPlaceholderText(
            "Enter or paste clinical data here..."
        )
        self.clinical_data_input.textChanged.connect(self.data_changed)

        # Configure a fixed height for the text area to save space
        self.clinical_data_input.setMinimumHeight(100)
        self.clinical_data_input.setMaximumHeight(150)

        # Set a smaller font for the clinical data input
        text_font = QFont()
        text_font.setPointSize(9)
        self.clinical_data_input.setFont(text_font)

        patient_layout.addRow("Patient ID:", self.patient_id_input)
        patient_layout.addRow("Clinical Data:", self.clinical_data_input)

        patient_group.setLayout(patient_layout)
        layout.addWidget(patient_group)

    def get_patient_data(self):
        """Get the patient data from the widget."""
        return {
            "patient_id": self.patient_id_input.text(),
            "clinical_data": self.clinical_data_input.toPlainText(),
        }

    def clear(self):
        """Clear all input fields."""
        self.patient_id_input.clear()
        self.clinical_data_input.clear()

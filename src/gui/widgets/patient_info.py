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

        # Pediatric Score Details (PEWS) Group - Hidden from GUI but kept for backend use
        self.pews_score_group = QGroupBox("Pediatric Score Details (PEWS)")
        pews_layout = QFormLayout()
        pews_layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_pews_behavior = QLineEdit("N/A")
        self.lbl_pews_behavior.setReadOnly(True)
        pews_layout.addRow("Behavior:", self.lbl_pews_behavior)
        
        self.lbl_pews_cardiovascular = QLineEdit("N/A")
        self.lbl_pews_cardiovascular.setReadOnly(True)
        pews_layout.addRow("Cardiovascular:", self.lbl_pews_cardiovascular)
        
        self.lbl_pews_respiratory = QLineEdit("N/A")
        self.lbl_pews_respiratory.setReadOnly(True)
        pews_layout.addRow("Respiratory:", self.lbl_pews_respiratory)
        
        self.lbl_pews_total = QLineEdit("N/A")
        self.lbl_pews_total.setReadOnly(True)
        total_pews_font = QFont()
        total_pews_font.setBold(True)
        self.lbl_pews_total.setFont(total_pews_font)
        self.lbl_pews_total.setStyleSheet("background-color: #e0e0e0;")
        pews_layout.addRow("Total PEWS:", self.lbl_pews_total)

        self.pews_score_group.setLayout(pews_layout)
        # Don't add to layout to hide from GUI
        # layout.addWidget(self.pews_score_group)
        
        # Store scores internally without displaying
        self.scoring_data = {}

    def get_patient_data(self):
        """Get the patient data from the widget."""
        return {
            "patient_id": self.patient_id_input.text(),
            "clinical_data": self.clinical_data_input.toPlainText(),
        }

    def set_patient_scores(self, scoring_results: dict):
        """
        Sets the PEWS score details in the UI.
        Args:
            scoring_results: A dictionary containing scoring data,
                             e.g., {'pews': {'total': 5, 'behavior': 1, 'cardiovascular': 2, 'respiratory': 2}}
        """
        pews_scores = scoring_results.get("pews", {})
        
        self.lbl_pews_behavior.setText(str(pews_scores.get("behavior", "N/A")))
        self.lbl_pews_cardiovascular.setText(str(pews_scores.get("cardiovascular", "N/A")))
        self.lbl_pews_respiratory.setText(str(pews_scores.get("respiratory", "N/A")))
        
        total_score = pews_scores.get("total") # Changed from "total_score" to "total" to match example data
        if total_score is not None:
            self.lbl_pews_total.setText(str(total_score))
            # Basic color coding for total score
            if isinstance(total_score, (int, float)):
                if total_score >= 7: # Example threshold for high risk
                    self.lbl_pews_total.setStyleSheet("background-color: #ffcccc;") # Light red
                elif total_score >= 4: # Example threshold for medium risk
                    self.lbl_pews_total.setStyleSheet("background-color: #ffffcc;") # Light yellow
                else:
                    self.lbl_pews_total.setStyleSheet("background-color: #ccffcc;") # Light green
            else:
                self.lbl_pews_total.setStyleSheet("background-color: #e0e0e0;") # Default if not a number
        else:
            self.lbl_pews_total.setText("N/A")
            self.lbl_pews_total.setStyleSheet("background-color: #e0e0e0;")


    def clear(self):
        """Clear all input fields and score displays."""
        self.patient_id_input.clear()
        self.clinical_data_input.clear()
        
        self.lbl_pews_behavior.setText("N/A")
        self.lbl_pews_behavior.setStyleSheet("background-color: #f0f0f0;")
        self.lbl_pews_cardiovascular.setText("N/A")
        self.lbl_pews_cardiovascular.setStyleSheet("background-color: #f0f0f0;")
        self.lbl_pews_respiratory.setText("N/A")
        self.lbl_pews_respiratory.setStyleSheet("background-color: #f0f0f0;")
        self.lbl_pews_total.setText("N/A")
        self.lbl_pews_total.setStyleSheet("background-color: #e0e0e0;")

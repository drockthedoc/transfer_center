from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit, 
    QGroupBox, QScrollArea, QTextBrowser, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Optional, Dict, List, Any

# Actual model imports
from ...core.models import PatientData, Location

class PatientInfoWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Patient Information")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        widget_in_scroll = QWidget()
        form_layout = QFormLayout(widget_in_scroll)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)

        # --- Patient Identifiers ---
        id_group = QGroupBox("Patient Identification")
        id_layout = QFormLayout()
        self.patient_id_edit = QLineEdit()
        id_layout.addRow("Patient ID:", self.patient_id_edit)
        id_group.setLayout(id_layout)
        form_layout.addRow(id_group)

        # --- Clinical Text Input ---
        clinical_text_group = QGroupBox("Clinical Narrative / Chief Complaint")
        clinical_text_layout = QVBoxLayout()
        self.clinical_text_edit = QTextEdit()
        self.clinical_text_edit.setPlaceholderText("Enter patient's clinical notes, chief complaint, history...")
        self.clinical_text_edit.setMinimumHeight(150)
        clinical_text_layout.addWidget(self.clinical_text_edit)
        clinical_text_group.setLayout(clinical_text_layout)
        form_layout.addRow(clinical_text_group)

        # --- Extracted & Derived Information (Read-only) ---
        derived_info_group = QGroupBox("Processed Information (Read-only)")
        derived_layout = QFormLayout()

        self.chief_complaint_display = QLabel("N/A")
        self.clinical_history_display = QTextBrowser()
        self.clinical_history_display.setReadOnly(True)
        self.clinical_history_display.setFrameStyle(QFrame.NoFrame)
        self.clinical_history_display.setFixedHeight(80)
        
        self.vital_signs_display = QTextBrowser()
        self.vital_signs_display.setReadOnly(True)
        self.vital_signs_display.setFrameStyle(QFrame.NoFrame)
        self.vital_signs_display.setFixedHeight(80)

        self.labs_display = QTextBrowser()
        self.labs_display.setReadOnly(True)
        self.labs_display.setFrameStyle(QFrame.NoFrame)
        self.labs_display.setFixedHeight(80)

        self.current_location_display = QLabel("N/A")
        self.extracted_data_display = QTextBrowser()
        self.extracted_data_display.setReadOnly(True)
        self.extracted_data_display.setFrameStyle(QFrame.NoFrame)
        self.extracted_data_display.setFixedHeight(100)

        self.care_needs_display = QTextBrowser()
        self.care_needs_display.setReadOnly(True)
        self.care_needs_display.setFrameStyle(QFrame.NoFrame)
        self.care_needs_display.setFixedHeight(80)
        
        self.care_level_display = QLabel("N/A")

        derived_layout.addRow("Inferred Chief Complaint:", self.chief_complaint_display)
        derived_layout.addRow("Inferred Clinical History:", self.clinical_history_display)
        derived_layout.addRow("Vital Signs:", self.vital_signs_display)
        derived_layout.addRow("Lab Results:", self.labs_display)
        derived_layout.addRow("Current Location:", self.current_location_display)
        derived_layout.addRow("LLM Extracted Data:", self.extracted_data_display)
        derived_layout.addRow("Identified Care Needs:", self.care_needs_display)
        derived_layout.addRow("Assessed Care Level:", self.care_level_display)
        derived_info_group.setLayout(derived_layout)
        form_layout.addRow(derived_info_group)

        scroll_area.setWidget(widget_in_scroll)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def _format_dict_to_html_simple(self, data: Dict[str, Any], title: Optional[str] = None) -> str:
        if not data:
            return "<p>N/A</p>"
        html = f"<b>{title}</b><br/>" if title else ""
        html += "<ul>"
        for key, value in data.items():
            html += f"<li><b>{key.replace('_', ' ').title()}:</b> {value}</li>"
        html += "</ul>"
        return html

    def _format_list_to_html_simple(self, data: List[str], title: Optional[str] = None) -> str:
        if not data:
            return "<p>N/A</p>"
        html = f"<b>{title}</b><br/>" if title else ""
        html += "<ul>"
        for item in data:
            html += f"<li>{item}</li>"
        html += "</ul>"
        return html

    def set_patient_data(self, patient_data: Optional[PatientData]):
        if not patient_data:
            self.clear_fields()
            return

        self.patient_id_edit.setText(getattr(patient_data, 'patient_id', ''))
        self.clinical_text_edit.setText(getattr(patient_data, 'clinical_text', ''))
        
        self.chief_complaint_display.setText(getattr(patient_data, 'chief_complaint', 'N/A') or 'N/A')
        self.clinical_history_display.setHtml(getattr(patient_data, 'clinical_history', 'N/A') or 'N/A')
        
        vitals = getattr(patient_data, 'vital_signs', {})
        self.vital_signs_display.setHtml(self._format_dict_to_html_simple(vitals))
        
        labs = getattr(patient_data, 'labs', {})
        self.labs_display.setHtml(self._format_dict_to_html_simple(labs))
        
        location = getattr(patient_data, 'current_location', None)
        if location:
            self.current_location_display.setText(f"Lat: {getattr(location, 'latitude', 'N/A')}, Lon: {getattr(location, 'longitude', 'N/A')}")
        else:
            self.current_location_display.setText("N/A")
            
        extracted = getattr(patient_data, 'extracted_data', {})
        self.extracted_data_display.setHtml(self._format_dict_to_html_simple(extracted))
        
        care_needs_list = getattr(patient_data, 'care_needs', [])
        self.care_needs_display.setHtml(self._format_list_to_html_simple(care_needs_list))
        
        self.care_level_display.setText(getattr(patient_data, 'care_level', 'N/A') or 'N/A')

    def get_patient_data(self) -> PatientData:
        patient_id_text = self.patient_id_edit.text().strip()
        clinical_text_content = self.clinical_text_edit.toPlainText().strip()

        try:
            data = PatientData(
                patient_id=patient_id_text,
                clinical_text=clinical_text_content
            )
            return data
        except Exception as e: 
            print(f"Error creating PatientData in PatientInfoWidget: {e}") 
            raise

    def clear_fields(self):
        self.patient_id_edit.clear()
        self.clinical_text_edit.clear()
        self.chief_complaint_display.setText("N/A")
        self.clinical_history_display.setHtml("N/A")
        self.vital_signs_display.setHtml("N/A")
        self.labs_display.setHtml("N/A")
        self.current_location_display.setText("N/A")
        self.extracted_data_display.setHtml("N/A")
        self.care_needs_display.setHtml("N/A")
        self.care_level_display.setText("N/A")

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    class DummyLocation:
        def __init__(self, latitude, longitude):
            self.latitude = latitude
            self.longitude = longitude

    class DummyPatientData:
        def __init__(self):
            self.patient_id = "PT12345"
            self.clinical_text = "65 y/o male presents with chest pain and shortness of breath. History of hypertension."
            self.chief_complaint = "Chest pain, shortness of breath"
            self.clinical_history = "Hypertension, previous MI in 2018."
            self.vital_signs = {"HR": "95 bpm", "BP": "160/90 mmHg", "RR": "22/min", "SpO2": "92%"}
            self.labs = {"Troponin I": "0.5 ng/mL", "BNP": "600 pg/mL"}
            self.current_location = DummyLocation(latitude=29.7604, longitude=-95.3698)
            self.extracted_data = {"condition": "Suspected Acute Coronary Syndrome", "age": "65", "sex": "male"}
            self.care_needs = ["Cardiac monitoring", "Oxygen therapy", "Cardiology consult"]
            self.care_level = "ICU"

    app = QApplication(sys.argv)
    PatientInfoWidget.PatientData = DummyPatientData 
    PatientInfoWidget.Location = DummyLocation
    
    widget = PatientInfoWidget()
    
    p_data = DummyPatientData()
    widget.set_patient_data(p_data)
    widget.show()

    sys.exit(app.exec_())

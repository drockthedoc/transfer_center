"""
Main window for the Transfer Center GUI application.

This module implements the main application window using PyQt5 with a refactored,
component-based architecture for improved maintainability.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.core.decision_engine import recommend_campus
from src.core.models import (
    HospitalCampus,
    Location,
    MetroArea,
    PatientData,
    Recommendation,
    TransferRequest,
    TransportMode,
    WeatherData,
    LLMReasoningDetails # Added import
)
from src.gui.widgets.census_data import CensusDataWidget
from src.gui.widgets.hospital_search_widget import HospitalSearchWidget
from src.gui.widgets.llm_settings import LLMSettingsWidget
from src.gui.widgets.patient_info import PatientInfoWidget
from src.gui.widgets.recommendation_output import RecommendationOutputWidget
from src.gui.widgets.transport_options import TransportOptionsWidget
from src.llm.llm_classifier_refactored import LLMClassifier
from src.utils.census_updater import update_census
from src.utils.transport.estimator import TransportTimeEstimator
# Import for robust recommendation handling if it's used directly here,
# otherwise ensure it's correctly used within _process_recommendation.
from src.llm.robust_recommendation_handler import RecommendationHandler


logger = logging.getLogger(__name__)


class TransferCenterMainWindow(QMainWindow):
    """Main window for the Transfer Center GUI application."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Texas Children's Hospital - Transfer Center")
        self.setMinimumSize(1200, 800)

        app_font = QFont()
        app_font.setPointSize(9)
        QApplication.setFont(app_font)

        self.hospitals: List[HospitalCampus] = []
        self.weather_data: Optional[WeatherData] = None
        self.llm_classifier = LLMClassifier()
        self.transport_estimator = TransportTimeEstimator()
        self.settings = QSettings("TCH", "TransferCenter")

        self.last_census_update = self.settings.value(
            "census/last_update", "Never", str
        )
        self.census_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "current_census.csv",
        )
        self.hospital_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "sample_hospital_campuses.json",
        )

        self._init_ui()
        self._load_config()

    def _extract_basic_data(self, patient: Union[PatientData, Dict], clinical_text: str) -> Dict:
        """Extract basic patient data for scoring from clinical text using rule-based methods.
        
        Args:
            patient: Either a PatientData object or a dictionary containing patient data
            clinical_text: The raw clinical text to analyze
            
        Returns:
            Dictionary with extracted data including vital signs
        """
        import re

        extracted_data = {}
        vital_signs = {}

        age_match = re.search(
            r"(\d+)(?:\s*-|\s+)(?:year|yr|y)[s\s]*(?:old)?",
            clinical_text,
            re.IGNORECASE,
        )
        if age_match:
            extracted_data["age_years"] = int(age_match.group(1))

        months_match = re.search(
            r"(\d+)(?:\s*-|\s+)(?:month|mo|m)[s\s]*(?:old)?",
            clinical_text,
            re.IGNORECASE,
        )
        if months_match:
            extracted_data["age_months"] = int(months_match.group(1))

        hr_match = re.search(
            r"(?:HR|heart rate|pulse)[:\s]+(\d+)", clinical_text, re.IGNORECASE
        )
        if hr_match:
            vital_signs["heart_rate"] = int(hr_match.group(1))

        rr_match = re.search(
            r"(?:RR|resp(?:iratory)? rate)[:\s]+(\d+)", clinical_text, re.IGNORECASE
        )
        if rr_match:
            vital_signs["respiratory_rate"] = int(rr_match.group(1))

        bp_match = re.search(
            r"(?:BP|blood pressure)[:\s]+(\d+)[/\\](\d+)", clinical_text, re.IGNORECASE
        )
        if bp_match:
            vital_signs["systolic_bp"] = int(bp_match.group(1))
            vital_signs["diastolic_bp"] = int(bp_match.group(2))

        o2_match = re.search(
            r"(?:O2 sat|SpO2|oxygen saturation)[:\s]+(\d+)(?:\s*%)?",
            clinical_text,
            re.IGNORECASE,
        )
        if o2_match:
            vital_signs["oxygen_saturation"] = int(o2_match.group(1))

        temp_match = re.search(
            r"(?:temp|temperature)[:\s]+(\d+\.?\d*)", clinical_text, re.IGNORECASE
        )
        if temp_match:
            vital_signs["temperature"] = float(temp_match.group(1))

        weight_match = re.search(
            r"(?:weight)[:\s]+(\d+\.?\d*)\s*(?:kg)", clinical_text, re.IGNORECASE
        )
        if weight_match:
            extracted_data["weight_kg"] = float(weight_match.group(1))

        extracted_data["vital_signs"] = vital_signs

        if isinstance(patient, PatientData) and hasattr(patient, 'extracted_data') and isinstance(patient.extracted_data, dict):
            patient.extracted_data.update(extracted_data)
        elif isinstance(patient, dict) and 'extracted_data' in patient and isinstance(patient['extracted_data'], dict):
             patient['extracted_data'].update(extracted_data)
        
        return extracted_data

    def _init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(3)

        self.patient_widget = PatientInfoWidget()
        left_layout.addWidget(self.patient_widget)

        self.hospital_search_widget = HospitalSearchWidget()
        self.hospital_search_widget.hospital_selected.connect(
            self._handle_hospital_selection
        )
        left_layout.addWidget(self.hospital_search_widget)

        self.transport_widget = TransportOptionsWidget()
        left_layout.addWidget(self.transport_widget)

        self.census_widget = CensusDataWidget()
        self.census_widget.census_updated.connect(self._update_census_data)
        self.census_widget.display_summary.connect(self._display_census_summary)
        self.census_widget.browse_button.clicked.connect(self._browse_census_file)
        left_layout.addWidget(self.census_widget)

        self.submit_button = QPushButton("Generate Recommendation")
        self.submit_button.setMinimumHeight(40)
        self.submit_button.clicked.connect(self._on_submit)
        left_layout.addWidget(self.submit_button)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(3)

        self.recommendation_widget = RecommendationOutputWidget()
        right_layout.addWidget(self.recommendation_widget)

        self.llm_settings_widget = LLMSettingsWidget()
        self.llm_settings_widget.refresh_models.connect(self._refresh_llm_models)
        self.llm_settings_widget.test_connection.connect(self._test_llm_connection)
        self.llm_settings_widget.settings_changed.connect(self._save_settings)
        right_layout.addWidget(self.llm_settings_widget)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])

        main_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def _handle_hospital_selection(self, hospital_data):
        self.statusBar.showMessage(f"Selected hospital: {hospital_data['name']}")

    def _browse_census_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Census CSV File", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.census_file_path = file_path
            self.census_widget.set_file_path(file_path)
            self.statusBar.showMessage(f"Selected census file: {file_path}")

    def _update_census_data(self):
        if not self.census_file_path or not os.path.exists(self.census_file_path):
            QMessageBox.warning(
                self,
                "Census Update Error",
                "No census file selected or file does not exist.",
            )
            return

        try:
            self.statusBar.showMessage("Updating census data...")
            success = update_census(self.census_file_path, self.hospital_file_path)
            updated_hospitals_data = None
            if success:
                try:
                    with open(self.hospital_file_path, "r") as f:
                        updated_hospitals_data = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading updated hospital data: {str(e)}")
            
            if updated_hospitals_data:
                # Re-create HospitalCampus objects
                self.hospitals = []
                for campus_data in updated_hospitals_data:
                    self.hospitals.append(self._create_hospital_campus_from_data(campus_data))

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.last_census_update = timestamp
                self.settings.setValue("census/last_update", timestamp)
                self.census_widget.set_last_update(timestamp)

                status_html = "<p><b>Census data updated successfully.</b></p>"
                status_html += f"<p>Updated at: {timestamp}</p>"
                status_html += f"<p>Updated {len(self.hospitals)} hospitals.</p>"
                self.census_widget.set_status(status_html)
                self.statusBar.showMessage("Census data updated successfully")
            else:
                self.census_widget.set_status("<p><b>Error updating census data. Check logs.</b></p>")
                self.statusBar.showMessage("Error updating census data")

        except Exception as e:
            logger.error(f"Error updating census data: {str(e)}")
            self.census_widget.set_status(f"<p><b>Error:</b> {str(e)}</p>")
            self.statusBar.showMessage("Error updating census data")

    def _display_census_summary(self):
        if not self.hospitals:
            QMessageBox.information(self, "Census Summary", "No hospital data loaded.")
            return

        try:
            summary = "<h3>Current Census Summary</h3>"
            summary += f"<p><b>Last Updated:</b> {self.last_census_update}</p>"
            summary += "<table border='1' cellspacing='0' cellpadding='3' width='100%'>"
            summary += "<tr><th>Hospital</th><th>General Beds</th><th>ICU Beds</th><th>NICU Beds</th></tr>"

            for hospital in self.hospitals:
                bc = hospital.bed_census # BedCensus object
                summary += f"<tr><td>{hospital.name}</td>"
                summary += f"<td>{bc.available_beds}/{bc.total_beds}</td>"
                summary += f"<td>{bc.icu_beds_available}/{bc.icu_beds_total}</td>"
                summary += f"<td>{bc.nicu_beds_available}/{bc.nicu_beds_total}</td></tr>"
            summary += "</table>"
            self.recommendation_widget.set_recommendation({'main': summary}) # Display in main area

        except Exception as e:
            logger.error(f"Error displaying census summary: {str(e)}")
            QMessageBox.warning(
                self, "Census Summary Error", f"Error generating summary: {str(e)}"
            )
            
    def _create_hospital_campus_from_data(self, campus_data: Dict) -> HospitalCampus:
        """Helper to create HospitalCampus object from dictionary data."""
        return HospitalCampus(
            campus_id=campus_data.get("campus_id", ""),
            name=campus_data.get("name", ""),
            metro_area=MetroArea(campus_data.get("metro_area", "HOUSTON_METRO")),
            address=campus_data.get("address", ""),
            location=Location(
                latitude=campus_data.get("location", {}).get("latitude", 0),
                longitude=campus_data.get("location", {}).get("longitude", 0),
            ),
            # Ensure bed_census is correctly parsed into a BedCensus object if your model expects that
            # For now, assuming HospitalCampus constructor handles a dict for bed_census
            bed_census=campus_data.get("bed_census", {}),
            exclusions=campus_data.get("exclusions", []),
            helipads=campus_data.get("helipads", []), 
        )

    def _load_config(self):
        try:
            if os.path.exists(self.hospital_file_path):
                with open(self.hospital_file_path, "r") as f:
                    hospital_data_list = json.load(f)
                self.hospitals = [self._create_hospital_campus_from_data(data) for data in hospital_data_list]
                logger.info(f"Loaded {len(self.hospitals)} hospitals")
                self.statusBar.showMessage(f"Loaded {len(self.hospitals)} hospitals")
            else:
                logger.warning(f"Hospital data file not found: {self.hospital_file_path}")
                self.statusBar.showMessage("Hospital data file not found")

            api_url = self.settings.value("llm/api_url", "http://localhost:1234/v1", str)
            model = self.settings.value("llm/model", "", str)
            self.llm_classifier.set_api_url(api_url)
            if model:
                self.llm_classifier.set_model(model)

            self.llm_settings_widget.api_url_input.setText(api_url)
            self._refresh_llm_models() 

            self.census_widget.set_last_update(self.last_census_update)
            self.census_widget.set_file_path(self.census_file_path)

        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self.statusBar.showMessage("Error loading configuration")

    def _save_settings(self):
        self.settings.setValue("llm/api_url", self.llm_settings_widget.api_url_input.text())
        self.settings.setValue("llm/model", self.llm_settings_widget.model_input.currentText())

    def _refresh_llm_models(self):
        try:
            api_url = self.llm_settings_widget.api_url_input.text()
            self.llm_classifier.set_api_url(api_url)
            models = self.llm_classifier.refresh_models()
            if models:
                self.llm_settings_widget.set_models(models)
                self.llm_settings_widget.set_status(
                    f"<p><b>Found {len(models)} models.</b></p>"
                )
                self.statusBar.showMessage(f"Found {len(models)} models")
            else:
                self.llm_settings_widget.set_status("<p><b>No models found. Ensure LM Studio is running.</b></p>")
                self.statusBar.showMessage("No models found")
        except Exception as e:
            logger.error(f"Error refreshing models: {str(e)}")
            self.llm_settings_widget.set_status(f"<p><b>Error:</b> {str(e)}</p>")
            self.statusBar.showMessage("Error refreshing models")

    def _test_llm_connection(self):
        try:
            api_url = self.llm_settings_widget.api_url_input.text()
            model = self.llm_settings_widget.model_input.currentText()
            self.statusBar.showMessage("Testing LLM connection...")
            self.llm_settings_widget.set_status("<p>Testing connection...</p>")
            success, message = self.llm_classifier.test_connection(api_url, model)
            if success:
                self.llm_settings_widget.set_status(f"<p><b>Connection successful!</b> Model: {model}</p>")
                self.statusBar.showMessage("LLM connection successful")
            else:
                self.llm_settings_widget.set_status(f"<p><b>Connection failed!</b> Error: {message}</p>")
                self.statusBar.showMessage("LLM connection failed")
        except Exception as e:
            logger.error(f"Error testing connection: {str(e)}")
            self.llm_settings_widget.set_status(f"<p><b>Error:</b> {str(e)}</p>")
            self.statusBar.showMessage("Error testing connection")

    def _on_submit(self):
        import traceback
        from datetime import datetime
        
        self.recommendation_widget.clear()
        self.statusBar.showMessage("Preparing recommendation...")
        
        try:
            patient_form_data = self.patient_widget.get_patient_data()
            location_data = self.hospital_search_widget.get_location_data()
            transport_data = self.transport_widget.get_transport_data()
            
            if not patient_form_data.get("clinical_data"):
                QMessageBox.warning(self, "Missing Data", "Please enter clinical data.")
                return
            if not location_data:
                QMessageBox.warning(self, "Missing Data", "Please select a sending facility location.")
                return
            
            clinical_text = patient_form_data["clinical_data"]
            
            # Use rule-based extraction as a base/fallback
            basic_data_from_rules = self._extract_basic_data({}, clinical_text) # Pass empty dict as patient for this stage
            
            # Prepare PatientData object
            patient = PatientData(
                patient_id=patient_form_data.get("patient_id") or "UNKNOWN",
                clinical_text=clinical_text,
                extracted_data=basic_data_from_rules, # Start with rule-based
                care_needs=basic_data_from_rules.get("keywords", []), # Placeholder, LLM might override
                care_level=basic_data_from_rules.get("suggested_care_level", "General") # Placeholder
            )
            
            # Scoring results (if applicable, adapt if you have a scoring_widget)
            scoring_results = None
            # if hasattr(self, "scoring_widget") and self.scoring_widget:
            #     try:
            #         scoring_results = self.scoring_widget.get_scoring_results()
            #     except Exception as score_error:
            #         logger.warning(f"Error getting scoring results: {score_error}")

            request = TransferRequest(
                request_id=f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                patient_data=patient, # PatientData object
                clinical_notes=clinical_text, # Keep raw notes too
                sending_location=Location(
                    latitude=location_data["latitude"],
                    longitude=location_data["longitude"],
                ),
                requested_datetime=datetime.now(),
                transport_mode=(
                    TransportMode.GROUND_AMBULANCE if transport_data["transport_mode"] == "Ground"
                    else TransportMode.HELICOPTER if transport_data["transport_mode"] == "Helicopter"
                    else TransportMode.FIXED_WING
                ),
                transport_info={
                    "type": transport_data["transport_type"],
                    "mode": transport_data["transport_mode"],
                    "departure_time": transport_data["departure_time"],
                    # Store these here since they're not attributes of TransferRequest
                    "clinical_text": clinical_text,
                    "scoring_results": scoring_results,
                    "human_suggestions": patient_form_data.get("human_suggestions"),
                },
            )
            
            self._process_recommendation(request)
            
        except Exception as e:
            logger.error(f"Critical error in form submission: {str(e)}\n{traceback.format_exc()}")
            self.statusBar.showMessage(f"Error: {str(e)}")
            self.recommendation_widget.set_recommendation( # Pass string for error display
                f"<h3>Error During Submission</h3><p>{str(e)}</p>"
            )
    
    def _process_recommendation(self, request: TransferRequest) -> None:
        """Process a transfer request and generate a recommendation with enhanced fallback and error handling.
        
        This implementation provides multi-layered fallback and full error recovery:
        1. First attempt rule-based extraction for fallback option
        2. Then try LLM processing with comprehensive error handling
        3. Fall back to rule-based if LLM fails
        4. Generate error recommendation if all else fails
        """
        import traceback
        
        self.recommendation_widget.clear()
        self.statusBar.showMessage("Generating recommendation...")
        
        try:
            # Prepare data for LLM processing
            clinical_text = request.clinical_notes
            human_suggestions = request.human_suggestions
            scoring_results = request.scoring_results
            patient_data_for_llm = request.patient_data # This is already a dict or None

            sending_facility_location_dict = None
            if request.sending_facility_location:
                sending_facility_location_dict = {
                    'latitude': request.sending_facility_location.latitude,
                    'longitude': request.sending_facility_location.longitude
                }
                logger.info(f"Prepared sending_facility_location_dict: {sending_facility_location_dict}")
            else:
                logger.warning("sending_facility_location not available in request for LLM processing.")

            # hospital_options and census_data are prepared earlier in this method
            logger.info(f"Passing {len(self.hospitals)} available hospitals (hospital_options) to LLMClassifier.process_text")
            logger.info(f"Passing census_data to LLMClassifier.process_text: {'present' if self.census_widget.census_data else 'absent'}")

            # Single call to the refactored LLMClassifier.process_text
            llm_data = self.llm_classifier.process_text(
                text=clinical_text,
                patient_data=patient_data_for_llm,
                sending_facility_location=sending_facility_location_dict,
                available_hospitals=self.hospitals, # Use hospital_options directly
                census_data=self.census_widget.census_data,
                human_suggestions=human_suggestions,
                scoring_results=scoring_results
            )

            llm_processing_successful = llm_data.get("success", False)
            final_recommendation = llm_data.get("final_recommendation") # This is now the Recommendation object or None
            llm_error_message = llm_data.get("llm_error_message")

            if llm_processing_successful and final_recommendation:
                logger.info("LLM processing successful, using final recommendation from LLMClassifier.")
                # The final_recommendation object is already what we need.
                # No need to call recommendation_generator.generate_recommendation again.
            else:
                logger.warning(f"LLM processing failed or returned no recommendation. Error: {llm_error_message}. Falling back to rule-based.")
                # Fallback logic: Use rule-based recommendation
                # This part of the fallback might need to be adjusted if it relied on data
                # that was previously prepared differently.
                final_recommendation = RecommendationHandler.create_rule_based_recommendation(
                    request=request,
                    available_hospitals=self.hospitals, # Use self.hospitals for rule-based
                    reason=f"LLM processing failed ({llm_error_message if llm_error_message else 'unknown error'}); rule-based fallback used."
                )
                if final_recommendation:
                    logger.info(f"Generated rule-based fallback recommendation: {final_recommendation.recommended_campus_id}")
                else:
                    logger.error("Rule-based fallback also failed to generate a recommendation.")
                    # Handle critical failure - perhaps display an error message to the user
                    self.update_recommendation_display(None, error_message="Critical error: Could not generate any recommendation.")
                    return

            # Augment notes if needed (final_recommendation is now the Recommendation object)
            if final_recommendation:
                current_notes = getattr(final_recommendation, 'notes', []) or []
                if llm_error_message and not llm_processing_successful:
                    current_notes.append(f"LLM Error: {llm_error_message}")
                # Add other relevant notes if necessary
                final_recommendation.notes = current_notes

            # Update the display with the final recommendation (either LLM or rule-based)
            self.update_recommendation_display(final_recommendation)

        except Exception as e:
            logger.error(f"Error in _process_recommendation: {e}", exc_info=True)
            self.update_recommendation_display(None, error_message=f"Error processing recommendation: {e}")

    def _display_recommendation(self, recommendation: Recommendation) -> None:
        logger.info(f"Displaying recommendation for: {getattr(recommendation, 'recommended_campus_id', 'N/A')}")
        
        method_text = ""
        explain_details = getattr(recommendation, 'explainability_details', None)
        
        if isinstance(explain_details, dict):
            extraction_method = explain_details.get("extraction_method", "unknown")
            if "error" in explain_details or extraction_method == "error": # Check for error indication
                method_text = "<b>[Error in Recommendation Process]</b>"
            elif extraction_method == "rule_based":
                method_text = "<b>[Generated using Rule-Based Extraction]</b>"
            elif extraction_method == "llm":
                method_text = "<b>[Generated using AI/LLM Processing]</b>"
        elif isinstance(explain_details, str) and "error" in explain_details.lower():
             method_text = "<b>[Error in Recommendation Process]</b>"


        formatted_output = {
            'main': self._format_main_recommendation(recommendation, method_text),
            'transport': self._format_transport_info(recommendation),
            'conditions': self._format_conditions_info(recommendation),
            'exclusions': self._format_exclusions_info(recommendation),
            'alternatives': self._format_alternatives_info(recommendation),
            'scoring': self._format_scoring_results(recommendation),
            'urgency': self._determine_urgency(recommendation)
        }
        
        # Updated call to set_recommendation
        self.recommendation_widget.set_recommendation(formatted_data=formatted_output, raw_recommendation=recommendation)
        
        # Format and set explanation tab
        explanation_html = self._format_explanation_html(recommendation)
        self.recommendation_widget.set_explanation(explanation_html)

        # Optionally set raw data if your Recommendation object or handler provides it
        # raw_data_html = self._format_raw_data_html(recommendation) # Example
        # self.recommendation_widget.set_raw_data(raw_data_html)

    def _format_scoring_results(self, recommendation: Recommendation) -> str:
        """Format clinical scoring results into an HTML string."""
        if not getattr(recommendation, 'scoring_results', None):
            return "<p>No clinical scoring results available for this recommendation.</p>"

        scoring_html = "<div style='margin-bottom: 10px;'>"
        scoring_html += "<h4 style='color: #2c3e50; margin-bottom: 5px;'>Clinical Scoring Details:</h4>"
        
        for sr in recommendation.scoring_results:
            scoring_html += "<div style='border: 1px solid #e0e0e0; padding: 8px; margin-bottom: 8px; border-radius: 4px; background-color: #f9f9f9;'>"
            scoring_html += f"<p style='margin: 2px 0;'><b>Scorer:</b> {sr.scorer_name}</p>"
            score_value_display = sr.score_value if sr.score_value is not None else 'N/A'
            scoring_html += f"<p style='margin: 2px 0;'><b>Score:</b> {score_value_display}</p>"
            if sr.interpretation:
                scoring_html += f"<p style='margin: 2px 0;'><b>Interpretation:</b> {sr.interpretation}</p>"
            if sr.details:
                scoring_html += "<p style='margin: 2px 0;'><b>Details:</b></p><ul style='margin-top: 2px; padding-left: 20px;'>"
                for key, value in sr.details.items():
                    scoring_html += f"<li><em>{key.replace('_', ' ').title()}:</em> {value}</li>"
                scoring_html += "</ul>"
            # Timestamp is available: sr.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            # Consider if timestamp needs to be displayed here or if it's too verbose for this section.
            scoring_html += "</div>"
        
        scoring_html += "</div>"
        return scoring_html

    def _format_main_recommendation(self, recommendation: Recommendation, method_text: str) -> str:
        """Format the main recommendation section."""
        # Get the confidence score
        confidence = recommendation.confidence_score if hasattr(recommendation, 'confidence_score') and recommendation.confidence_score else "N/A"
        confidence_text = f"<span style='color:{'green' if confidence > 80 else 'orange' if confidence > 60 else 'red'};'>({confidence}% confidence)</span>" if isinstance(confidence, (int, float)) else ""
        
        # Get campus ID
        campus_id = getattr(recommendation, 'recommended_campus_id', "N/A")
        
        # Get care level primarily from the dedicated field
        care_level = getattr(recommendation, 'recommended_level_of_care', "Unknown")

        # Fallback to inferring from explainability_details if primary is missing or generic
        if not care_level or care_level in ["Unknown", "General"]:
            if hasattr(recommendation, 'explainability_details') and recommendation.explainability_details:
                details = recommendation.explainability_details
                # The LLM output uses 'care_level' in its JSON, which maps to 'recommended_level_of_care' in the Pydantic model.
                # However, if 'explainability_details' somehow directly contains a 'care_level' key from a different source, check it.
                if isinstance(details, dict) and 'care_level' in details and details['care_level'] and details['care_level'] not in ["Unknown", "General"]:
                    care_level = details['care_level']
        
        # Get clinical reasoning
        reasoning = ""
        if hasattr(recommendation, 'clinical_reasoning') and recommendation.clinical_reasoning:
            reasoning = recommendation.clinical_reasoning
        elif hasattr(recommendation, 'reason') and recommendation.reason:
            reasoning = recommendation.reason
                
        # If care level still unknown or generic after checking direct attribute and explainability_details, try to infer from clinical reasoning
        if not care_level or care_level in ["Unknown", "General"]:
            reasoning_lower = reasoning.lower() # Ensure reasoning is defined
            if "picu" in reasoning_lower or "pediatric intensive care" in reasoning_lower:
                care_level = "PICU"
            elif "nicu" in reasoning_lower or "neonatal intensive care" in reasoning_lower:
                care_level = "NICU"
            elif "icu" in reasoning_lower or "intensive care" in reasoning_lower:
                care_level = "ICU"
            elif "intermediate" in reasoning_lower:
                care_level = "Intermediate Care"
            elif "general" in reasoning_lower and "floor" in reasoning_lower:
                care_level = "General Floor"
        
        # Format the notes
        notes = ""
        if hasattr(recommendation, 'notes') and recommendation.notes:
            notes = "<br>".join([f"<li>{note}</li>" for note in recommendation.notes])
            notes = f"<p><b>Notes:</b><ul>{notes}</ul></p>" if notes else ""
        
        return f"""
        <h2>Recommended Campus: <span style='color:blue;'>{campus_id}</span> {confidence_text}</h2>
        <p>{method_text}</p>
        <p><b>Recommended Care Level:</b> {care_level}</p>
        <p><b>Clinical Reasoning:</b><br>{reasoning}</p>
        {notes}
        """
    
    def _format_transport_info(self, recommendation: Recommendation) -> str:
        logger.info("Formatting transport info for recommendation")
        
        # Get transport details from the recommendation object
        transport_details = getattr(recommendation, 'transport_details', {})
        logger.info(f"Transport details: {transport_details}")
        
        # Extract mode with fallbacks
        mode = "Not specified"
        if isinstance(transport_details, dict) and 'mode' in transport_details:
            mode = transport_details['mode']
            # Format mode nicely
            if isinstance(mode, str):
                mode = mode.replace('_', ' ').replace('GROUND_AMBULANCE', 'Ground Ambulance').replace('HELICOPTER', 'Helicopter').replace('FIXED_WING', 'Fixed Wing Aircraft').title()
        
        # Extract time with fallbacks
        est_time = "Not specified"
        for key in ['estimated_time_minutes', 'estimated_time', 'time_minutes', 'travel_time']:
            if isinstance(transport_details, dict) and key in transport_details:
                est_time_value = transport_details[key]
                if isinstance(est_time_value, (int, float)):
                    est_time = f"{est_time_value} minutes"
                else:
                    est_time = str(est_time_value)
                break
        
        # Get distance from transport details if available
        distance = "Not available"
        for key in ['distance', 'distance_km', 'distance_miles']:
            if isinstance(transport_details, dict) and key in transport_details:
                distance_value = transport_details[key]
                if isinstance(distance_value, (int, float)):
                    distance = f"{distance_value} km"
                else:
                    distance = str(distance_value)
                break
        
        # If distance not in transport details, calculate it
        if distance == "Not available":
            campus_id = getattr(recommendation, 'recommended_campus_id', None)
            if hasattr(self, 'current_transfer_request') and campus_id:
                try:
                    from src.utils.travel_calculator import calculate_distance
                    from src.utils.hospital_loader import load_hospitals
                    
                    # Get sender location
                    sender_location = self.current_transfer_request.location
                    
                    # Find hospital with matching ID
                    hospitals = load_hospitals()
                    for hospital in hospitals:
                        if hospital.campus_id == campus_id:
                            # Calculate distance
                            distance_km = calculate_distance(sender_location, hospital.location)
                            distance = f"{distance_km:.1f} km"
                            logger.info(f"Calculated distance to {campus_id}: {distance}")
                            break
                except Exception as e:
                    logger.error(f"Error calculating distance: {e}")
        
        # Get special requirements with fallbacks
        special_req = "None"
        if isinstance(transport_details, dict):
            special_req = transport_details.get('special_requirements', 
                          transport_details.get('requirements', 
                            transport_details.get('notes', 'None')))
        
        # Format with nice HTML
        return f"""
        <h3>Transport Information</h3>
        <p><b>Mode:</b> {mode}</p>
        <p><b>Estimated Time:</b> {est_time}</p>
        <p><b>Distance:</b> {distance}</p>
        <p><b>Special Requirements:</b> {special_req}</p>
        """
    
    def _format_conditions_info(self, recommendation: Recommendation) -> str:
        logger.info("Formatting conditions info for recommendation")
        conditions_data = getattr(recommendation, 'conditions', {})
        
        # Try to convert from string if needed
        if isinstance(conditions_data, str):
            try:
                import json
                conditions_data = json.loads(conditions_data)
                logger.info("Successfully converted conditions string to dict")
            except:
                logger.warning("Failed to convert conditions string to dict")
                conditions_data = {}

        if not isinstance(conditions_data, dict):
            logger.warning(f"conditions is not a dict: {type(conditions_data)}")
            conditions_data = {}

        # Extract weather with fallback
        weather_report = conditions_data.get('weather', None)
        if weather_report is None:
            # Try to find weather in explainability details
            explain_details = getattr(recommendation, 'explainability_details', {})
            if isinstance(explain_details, dict):
                weather_report = explain_details.get('weather', 'Not specified')
            else:
                weather_report = 'Not specified'
                
        logger.info(f"Weather report: {weather_report}")
        
        # Color-code the weather report
        weather_color = "#333333" 
        if isinstance(weather_report, str) and weather_report != 'Not specified':
            if any(c in weather_report.lower() for c in ["storm", "snow", "ice", "severe", "warning", "tornado", "hurricane"]):
                weather_color = "#cc0000"  # Red for severe weather
            elif any(c in weather_report.lower() for c in ["rain", "wind", "advisory", "fog", "thunder"]):
                weather_color = "#e68a00"  # Orange for moderate concerns
            else: # Fair, clear, sunny etc.
                 weather_color = "#008800"  # Green for good conditions
        weather_html = f"<span style='color: {weather_color};'>{weather_report}</span>"

        # Extract traffic with fallback
        traffic_report = conditions_data.get('traffic', None)
        if traffic_report is None:
            # Try to find traffic in explainability details
            explain_details = getattr(recommendation, 'explainability_details', {})
            if isinstance(explain_details, dict):
                traffic_report = explain_details.get('traffic', 'Not specified')
            else:
                traffic_report = 'Not specified'
                
        logger.info(f"Traffic report: {traffic_report}")
        
        # Color-code the traffic report
        traffic_color = "#333333"
        if isinstance(traffic_report, str) and traffic_report != 'Not specified':
            if any(level in traffic_report.lower() for level in ["heavy", "severe", "delay", "standstill", "accident", "closed"]):
                traffic_color = "#cc0000"  # Red for severe traffic
            elif any(level in traffic_report.lower() for level in ["moderate", "slow", "congestion"]):
                traffic_color = "#e68a00"  # Orange for moderate traffic
            else: # Light, clear
                traffic_color = "#008800"  # Green for good traffic
        traffic_html = f"<span style='color: {traffic_color};'>{traffic_report}</span>"
        
        # Add road condition if available
        road_report = conditions_data.get('road_conditions', 'Not specified')
        road_html = road_report
        if road_report != 'Not specified':
            road_html = f"<b>Road Conditions:</b> {road_report}</p>"
        
        # Add estimated arrival time if available
        eta = conditions_data.get('estimated_arrival_time', None)
        eta_html = ""
        if eta:
            eta_html = f"<p><b>Estimated Arrival Time:</b> {eta}</p>"
        
        if weather_report != 'Not specified' or traffic_report != 'Not specified':
            return f"""
            <h3>Conditions</h3>
            <p><b>Weather:</b> {weather_html}</p>
            <p><b>Traffic:</b> {traffic_html}</p>
            {eta_html}
            """
        return "<p>No specific condition data available.</p>"

    def _format_exclusions_info(self, recommendation: Recommendation) -> str:
        """Format exclusion information based on recommendation.exclusion_notes."""
        # This method now expects the whole recommendation object to potentially
        # access exclusion_notes or other relevant fields in the future.
        # For now, it uses 'exclusion_notes' as per the previous valid version.
        exclusions = getattr(recommendation, 'exclusion_notes', []) #
        
        if not exclusions or not isinstance(exclusions, list):
            return "<p>No exclusion notes applied or available.</p>"
            
        html = "<h4>Exclusions Applied:</h4><ul>"
        # Assuming exclusions is a list of strings or dicts
        for exclusion_item in exclusions:
            if isinstance(exclusion_item, dict):
                reason = exclusion_item.get("reason", "No reason provided")
                campus = exclusion_item.get("campus_id", "General Note")
                html += f"<li><b>{campus}:</b> {reason}</li>"
            elif isinstance(exclusion_item, str):
                 html += f"<li>{exclusion_item}</li>" # If it's just a list of string notes
            else:
                 html += f"<li>{str(exclusion_item)}</li>"

        html += "</ul>"
        
        # Check for a flag indicating if human review is explicitly needed due to exclusions
        if getattr(recommendation, 'human_review_required_due_to_exclusions', False):
             html = (
                "<div style='background-color: #ffeeee; border: 1px solid #ff0000; padding: 8px; margin-bottom: 10px;'>"
                "<h3 style='color: #cc0000; margin: 0;'>⚠️ EXCLUSIONS REQUIRE REVIEW</h3>"
                "<p style='color: #cc0000; margin-top: 5px;'>Human review strongly advised before proceeding.</p>"
                "</div>"
            ) + html
        
        return html
    
    def _format_alternatives_info(self, recommendation: Recommendation) -> str:
        alternative_campuses = getattr(recommendation, 'alternative_campuses', None)
        html = ""
        
        if isinstance(alternative_campuses, list) and alternative_campuses:
            alternatives_list_html = []
            for alt in alternative_campuses:
                if isinstance(alt, dict):
                    alt_id = alt.get('campus_id', 'Unknown Campus')
                    alt_reason = alt.get('reason', 'No specific reason provided')
                    alt_score = alt.get('score', None)
                    score_text = f" (Score: {alt_score})" if alt_score is not None else ""
                    alternatives_list_html.append(f"<li><b>{alt_id}</b>: {alt_reason}{score_text}</li>")
                elif isinstance(alt, str): # Simple list of alternative names
                    alternatives_list_html.append(f"<li>{alt}</li>")

            if alternatives_list_html:
                html = "<h3>Alternative Options</h3><ul>" + "".join(alternatives_list_html) + "</ul>"
            else:
                html = "<p>No alternative campuses provided.</p>"
        else:
            html = "<p>No alternative campuses provided.</p>"
        return html
        
    def _determine_urgency(self, recommendation: Recommendation) -> str:
        urgency = getattr(recommendation, 'urgency', None)
        if urgency and isinstance(urgency, str):
            return urgency.lower()
        
        care_level = getattr(recommendation, 'recommended_level_of_care', "")
        if isinstance(care_level, str):
            care_level_lower = care_level.lower()
            if any(keyword in care_level_lower for keyword in ['icu', 'critical', 'emergency', 'stat']):
                return 'critical'
            elif any(keyword in care_level_lower for keyword in ['urgent', 'high', 'expedited']):
                return 'high'
        return 'normal'
        
    def _format_explanation_html(self, recommendation: Recommendation) -> str:
        """Format the detailed explanation tab content with enhanced visual formatting."""
        logger.info("Formatting explanation HTML for recommendation")
        # explainability_details should be an LLMReasoningDetails object or None
        # due to Pydantic model validation and the ensure_explainability_details validator.
        details: Optional[LLMReasoningDetails] = getattr(recommendation, 'explainability_details', None)
        
        explanation_html = """
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">Recommendation Reasoning</h2>
        """
        
        if not details or not isinstance(details, LLMReasoningDetails):
            logger.warning(f"No valid LLMReasoningDetails found in recommendation. Details type: {type(details)}")
            explanation_html += "<p style='color: #e74c3c; font-style: italic;'>No detailed explanation available or data is in an unexpected format.</p></div>"
            return explanation_html
        
        # At this point, 'details' is a valid LLMReasoningDetails object.
        main_reason = details.main_recommendation_reason
        explanation_html += f"""
        <div style="background-color: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0;">
            <h3 style="color: #2c3e50; margin-top: 0;">Primary Reason</h3>
            <p style="font-size: 16px;">{main_reason}</p>
        </div>
        """
        
        if details.key_factors_considered:
            explanation_html += """
            <div style="margin: 15px 0;">
                <h3 style="color: #2c3e50;">Key Factors Considered</h3>
                <ul style="list-style-type: square;">
            """
            for factor in details.key_factors_considered:
                explanation_html += f"<li style='margin-bottom: 8px;'>{factor}</li>"
            explanation_html += "</ul></div>"
        
        if details.alternative_reasons:
            explanation_html += """
            <div style="margin: 15px 0;">
                <h3 style="color: #2c3e50;">Alternative Considerations</h3>
                <ul style="list-style-type: circle;">
            """
            for alt_campus_id, reason_text in details.alternative_reasons.items():
                explanation_html += f"<li style='margin-bottom: 8px;'><b>{alt_campus_id}:</b> {reason_text}</li>"
            explanation_html += "</ul></div>"

        if details.confidence_explanation:
            explanation_html += f"""
            <div style="margin: 15px 0; background-color: #eafaf1; border-left: 4px solid #2ecc71; padding: 15px;">
                <h3 style="color: #2c3e50; margin-top: 0;">Confidence Explanation</h3>
                <p style="font-size: 16px;">{details.confidence_explanation}</p>
            </div>
            """
            
        explanation_html += "</div>"  # Close the main container
        return explanation_html


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    main_window = TransferCenterMainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    # Basic logging setup for GUI
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("transfer_center_gui.log"),
            logging.StreamHandler()
        ]
    )
    main()
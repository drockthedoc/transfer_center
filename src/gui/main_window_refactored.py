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

from src.core.decision import recommend_campus
from src.core.models import (
    HospitalCampus,
    Location,
    MetroArea,
    PatientData,
    Recommendation,
    TransferRequest,
    TransportMode,
    WeatherData,
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
        
        # Get clinical text from transport_info or patient_data
        clinical_text = ""
        if hasattr(request, 'transport_info') and request.transport_info and 'clinical_text' in request.transport_info:
            clinical_text = request.transport_info['clinical_text']
        elif hasattr(request.patient_data, 'clinical_text'):
            clinical_text = request.patient_data.clinical_text
        if not clinical_text:
            self._display_recommendation(RecommendationHandler.create_error_recommendation(
                request_id=request.request_id,
                error_message="No clinical text found in the request."
            ))
            return

        final_recommendation = None
        try:
            logger.info(f"Processing transfer request {request.request_id} with {len(clinical_text)} characters")
            
            # Get LLM settings for this run
            api_url = self.llm_settings_widget.api_url_input.text()
            model = self.llm_settings_widget.model_input.currentText()
            self.llm_classifier.set_api_url(api_url)
            self.llm_classifier.set_model(model)

            # Get scoring results from transport_info if available
            scoring_results = None
            if hasattr(request, 'transport_info') and request.transport_info and 'scoring_results' in request.transport_info:
                scoring_results = request.transport_info['scoring_results']
                
            # Rule-based extraction as a fallback
            rule_based_rec = RecommendationHandler.extract_rule_based_recommendation(
                clinical_text=clinical_text,
                request_id=request.request_id,
                scoring_results=scoring_results
            )
            logger.info(f"Generated rule-based recommendation as fallback: {rule_based_rec.recommended_campus_id}")

            try:
                # Get human suggestions from transport_info if available
                human_suggestions = None
                if hasattr(request, 'transport_info') and request.transport_info and 'human_suggestions' in request.transport_info:
                    human_suggestions = request.transport_info['human_suggestions']
                
                # Get available hospitals to pass to the LLM
                available_hospitals = self.hospitals
                
                # Get census data if available
                census_data = None
                try:
                    if hasattr(self, 'census_data_widget') and self.census_data_widget:
                        census_data = self.census_data_widget.get_census_data()
                except Exception as e:
                    logger.warning(f"Could not get census data: {e}")
                
                # Format hospital options for the LLM
                hospital_options = []
                if available_hospitals:
                    for hospital in available_hospitals:
                        # Build hospital info with safety checks
                        hospital_info = {
                            "campus_id": getattr(hospital, 'campus_id', 'unknown'),
                            "name": getattr(hospital, 'name', 'Unknown Hospital')
                        }
                        
                        # Add care levels if available
                        if hasattr(hospital, 'care_levels'):
                            hospital_info['care_levels'] = hospital.care_levels
                        elif hasattr(hospital, 'level_of_care'):
                            hospital_info['care_levels'] = [hospital.level_of_care]
                        else:
                            hospital_info['care_levels'] = []
                            
                        # Add specialties if available
                        if hasattr(hospital, 'specialties'):
                            hospital_info['specialties'] = hospital.specialties
                        else:
                            hospital_info['specialties'] = []
                            
                        # Add location data if available
                        location = {}
                        if hasattr(hospital, 'location'):
                            location['latitude'] = getattr(hospital.location, 'latitude', None)
                            location['longitude'] = getattr(hospital.location, 'longitude', None)
                        else:
                            # Try direct lat/lng properties
                            location['latitude'] = getattr(hospital, 'latitude', None)
                            location['longitude'] = getattr(hospital, 'longitude', None)
                            
                        hospital_info['location'] = location
                        hospital_options.append(hospital_info)
                
                # Create context dictionary with all relevant information
                context = {
                    "available_hospitals": hospital_options,
                    "census_data": census_data,
                    "human_suggestions": human_suggestions,
                    "scoring_results": scoring_results
                }
                
                # Log what we're sending to the LLM
                logger.info(f"Passing {len(hospital_options)} hospitals to LLM for recommendation")
                
                # Attempt LLM processing with comprehensive context
                extracted_llm_data = self.llm_classifier.process_text(
                    clinical_text,
                    context=context
                )
                
                if extracted_llm_data:
                    # Note: extract_recommendation only accepts extracted_data and request_id parameters
                    final_recommendation = RecommendationHandler.extract_recommendation(
                        extracted_data=extracted_llm_data,
                        request_id=request.request_id
                    )
                    # Augment notes if needed
                    current_notes = getattr(final_recommendation, 'notes', []) or []
                    current_notes.append("Generated using LLM processing.")
                    final_recommendation.notes = current_notes
                else:
                    logger.warning("LLM returned empty data. Falling back to rule-based.")
                    final_recommendation = rule_based_rec
                    current_notes = getattr(final_recommendation, 'notes', []) or []
                    current_notes.append("LLM processing failed or returned no data; rule-based fallback used.")
                    final_recommendation.notes = current_notes

            except Exception as llm_error:
                logger.error(f"LLM processing error: {llm_error}\n{traceback.format_exc()}")
                logger.info("Falling back to rule-based recommendation due to LLM error.")
                final_recommendation = rule_based_rec
                current_notes = getattr(final_recommendation, 'notes', []) or []
                current_notes.append(f"LLM error ({str(llm_error)}); rule-based fallback used.")
                final_recommendation.notes = current_notes
            
        except Exception as outer_error:
            logger.error(f"Error during recommendation extraction: {outer_error}\n{traceback.format_exc()}")
            final_recommendation = RecommendationHandler.create_error_recommendation(
                request_id=request.request_id,
                error_message=f"Core extraction error: {str(outer_error)}"
            )
        
        if final_recommendation:
            self._display_recommendation(final_recommendation)
            self.statusBar.showMessage("Recommendation generated.")
        else:
            # This case should ideally not be reached if error recommendations are created
            self.statusBar.showMessage("Failed to generate recommendation.")
            self._display_recommendation(RecommendationHandler.create_error_recommendation(
                 request_id=request.request_id, error_message="Unknown error led to no recommendation."
            ))

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
            'exclusions': self._format_exclusions_info(recommendation), # Changed to pass recommendation
            'alternatives': self._format_alternatives_info(recommendation),
            'urgency': self._determine_urgency(recommendation)
        }
        
        self.recommendation_widget.set_recommendation(formatted_output)
        
        # Format and set explanation tab
        explanation_html = self._format_explanation_html(recommendation)
        self.recommendation_widget.set_explanation(explanation_html)

        # Optionally set raw data if your Recommendation object or handler provides it
        # raw_data_html = self._format_raw_data_html(recommendation) # Example
        # self.recommendation_widget.set_raw_data(raw_data_html)

    def _format_main_recommendation(self, recommendation: Recommendation, method_text: str) -> str:
        """Format the main recommendation section."""
        # Get the confidence score
        confidence = recommendation.confidence_score if hasattr(recommendation, 'confidence_score') and recommendation.confidence_score else "N/A"
        confidence_text = f"<span style='color:{'green' if confidence > 80 else 'orange' if confidence > 60 else 'red'};'>({confidence}% confidence)</span>" if isinstance(confidence, (int, float)) else ""
        
        # Get campus ID
        campus_id = getattr(recommendation, 'recommended_campus_id', "N/A")
        
        # Get care level and infer it from clinical reasoning if not set directly
        care_level = "Unknown"
        if hasattr(recommendation, 'recommended_level_of_care') and recommendation.recommended_level_of_care:
            care_level = recommendation.recommended_level_of_care
        # Try to extract from explainability details
        elif hasattr(recommendation, 'explainability_details') and recommendation.explainability_details:
            details = recommendation.explainability_details
            if isinstance(details, dict) and 'care_level' in details:
                care_level = details['care_level']
        
        # Get clinical reasoning
        reasoning = ""
        if hasattr(recommendation, 'clinical_reasoning') and recommendation.clinical_reasoning:
            reasoning = recommendation.clinical_reasoning
        elif hasattr(recommendation, 'reason') and recommendation.reason:
            reasoning = recommendation.reason
                
        # If care level still unknown, try to infer from clinical reasoning
        if care_level == "Unknown":
            # Look for care level mentions in the reasoning
            reasoning_lower = reasoning.lower()
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
        transport_details = getattr(recommendation, 'transport_details', None)
        if isinstance(transport_details, dict):
            mode = transport_details.get('mode', 'Not specified')
            est_time = transport_details.get('estimated_time', 'Not specified')
            special_req = transport_details.get('special_requirements', 'None')
            return f"""
            <h3>Transport Information</h3>
            <p><b>Mode:</b> {mode}</p>
            <p><b>Estimated Time:</b> {est_time}</p>
            <p><b>Special Requirements:</b> {special_req}</p>
            """
        return "<p>No specific transport details available.</p>"
    
    def _format_conditions_info(self, recommendation: Recommendation) -> str:
        conditions_data = getattr(recommendation, 'conditions', {})
        if not isinstance(conditions_data, dict):
            conditions_data = {}

        weather_report = conditions_data.get('weather', 'Not specified')
        weather_color = "#333333" 
        if isinstance(weather_report, str) and weather_report != 'Not specified':
            if any(c in weather_report.lower() for c in ["storm", "snow", "ice", "severe", "warning", "tornado", "hurricane"]):
                weather_color = "#cc0000"
            elif any(c in weather_report.lower() for c in ["rain", "wind", "advisory", "fog", "thunder"]):
                weather_color = "#e68a00"
            else: # Fair, clear, sunny etc.
                 weather_color = "#008800"
        weather_html = f"<span style='color: {weather_color};'>{weather_report}</span>"

        traffic_report = conditions_data.get('traffic', 'Not specified')
        traffic_color = "#333333"
        if isinstance(traffic_report, str) and traffic_report != 'Not specified':
            if any(level in traffic_report.lower() for level in ["heavy", "severe", "delay", "standstill", "accident", "closed"]):
                traffic_color = "#cc0000" 
            elif any(level in traffic_report.lower() for level in ["moderate", "slow", "congestion"]):
                traffic_color = "#e68a00"
            else: # Light, clear
                traffic_color = "#008800"
        traffic_html = f"<span style='color: {traffic_color};'>{traffic_report}</span>"
        
        if weather_report != 'Not specified' or traffic_report != 'Not specified':
            return f"""
            <h3>Conditions</h3>
            <p><b>Weather:</b> {weather_html}</p>
            <p><b>Traffic:</b> {traffic_html}</p>
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
        """Format the detailed explanation tab content."""
        # This is the primary method for generating explanation HTML.
        # The orphaned code block at the end of the class has been removed.
        details = getattr(recommendation, 'explainability_details', None)
        explanation_html = "<h2>Recommendation Explanation</h2>"

        if not isinstance(details, dict) or not details:
            explanation_html += "<p>No detailed explanation available.</p>"
            return explanation_html

        # Detailed Reasoning
        detailed_reasoning = details.get('detailed_reasoning')
        if detailed_reasoning:
            explanation_html += f"<h3>Detailed Reasoning</h3><p>{str(detailed_reasoning)}</p>"

        # Proximity Analysis
        proximity_analysis = details.get('proximity_analysis')
        if proximity_analysis:
            explanation_html += f"<h3>Proximity Analysis</h3><p>{str(proximity_analysis)}</p>"

        # Campus Scores
        campus_scores_data = details.get('campus_scores')
        if isinstance(campus_scores_data, dict):
            explanation_html += "<h3>Detailed Campus Scoring</h3>"
            for campus_key, scores in campus_scores_data.items(): # e.g. "primary", "backup_XYZ"
                if isinstance(scores, dict):
                    campus_name = scores.get('name', campus_key.replace('_', ' ').title())
                    explanation_html += f"<h4>Scores for: {campus_name}</h4>"
                    explanation_html += "<table border='1' cellpadding='5' style='border-collapse: collapse; width:100%;'>"
                    explanation_html += "<tr style='background-color:#f0f0f0;'><th>Criteria</th><th>Score</th><th>Weight</th><th>Weighted Score</th><th>Notes</th></tr>"
                    
                    total_weighted_score = 0
                    default_weights = {"location": 0.40, "care_level_match": 0.30, "capacity": 0.20, "specialty_availability": 0.10}
                    
                    for criteria_key, criteria_label in [
                        ("location", "Location"), ("care_level_match", "Care Level Match"),
                        ("capacity", "Capacity"), ("specialty_availability", "Specialty Availability"),
                        ("overall_suitability", "Overall Suitability") # Example of another potential score
                    ]:
                        score_value = scores.get(criteria_key, "N/A")
                        weight = scores.get(f"{criteria_key}_weight", default_weights.get(criteria_key))
                        score_notes = scores.get(f"{criteria_key}_notes", "")

                        weighted_score_str = "N/A"
                        if isinstance(score_value, (int, float)) and isinstance(weight, (int, float)):
                            weighted_val = score_value * weight
                            weighted_score_str = f"{weighted_val:.2f}"
                            total_weighted_score += weighted_val
                        
                        weight_str = f"{weight*100:.0f}%" if isinstance(weight, float) else (str(weight) if weight else "N/A")

                        explanation_html += f"<tr><td>{criteria_label}</td><td>{score_value}</td><td>{weight_str}</td><td>{weighted_score_str}</td><td>{score_notes}</td></tr>"
                    
                    explanation_html += f"<tr><td colspan='3'><b>Total Weighted Score</b></td><td><b>{total_weighted_score:.2f}</b></td><td></td></tr>"
                    explanation_html += "</table><br/>"

        # Campus Comparison
        campus_comparison = details.get('campus_comparison')
        if campus_comparison:
            explanation_html += f"<h3>Campus Comparison</h3><p>{str(campus_comparison)}</p>"

        # Other generic details if any category was not specifically handled above
        processed_keys = {'detailed_reasoning', 'proximity_analysis', 'campus_scores', 'campus_comparison', 'extraction_method'}
        for category, cat_details in details.items():
            if category not in processed_keys:
                explanation_html += f"<h4>{category.replace('_', ' ').title()}</h4>"
                if isinstance(cat_details, dict):
                    explanation_html += "<ul>" + "".join([f"<li><b>{k.replace('_', ' ').title()}:</b> {v}</li>" for k, v in cat_details.items()]) + "</ul>"
                elif isinstance(cat_details, list):
                    explanation_html += "<ul>" + "".join([f"<li>{item}</li>" for item in cat_details]) + "</ul>"
                else:
                    explanation_html += f"<p>{str(cat_details)}</p>"
        
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
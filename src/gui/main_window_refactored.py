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
from src.llm.llm_classifier_refactored import LLMClassifier
from src.utils.transport.estimator import TransportTimeEstimator
from src.gui.widgets.census_data import CensusDataWidget
from src.gui.widgets.hospital_search_widget import HospitalSearchWidget
from src.gui.widgets.llm_settings import LLMSettingsWidget
from src.gui.widgets.patient_info import PatientInfoWidget
from src.gui.widgets.recommendation_output import RecommendationOutputWidget
from src.gui.widgets.transport_options import TransportOptionsWidget
from src.utils.census_updater import update_census

logger = logging.getLogger(__name__)


class TransferCenterMainWindow(QMainWindow):
    """Main window for the Transfer Center GUI application."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Texas Children's Hospital - Transfer Center")
        self.setMinimumSize(1200, 800)

        # Use a more compact app-wide font
        app_font = QFont()
        app_font.setPointSize(9)
        QApplication.setFont(app_font)

        # State variables
        self.hospitals: List[HospitalCampus] = []
        self.weather_data: Optional[WeatherData] = None
        self.llm_classifier = LLMClassifier()
        self.transport_estimator = TransportTimeEstimator()
        self.settings = QSettings("TCH", "TransferCenter")

        # Census update tracking
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

        # Initialize UI
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        """Initialize the user interface."""
        # Central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Create splitter for adjustable sections
        splitter = QSplitter(Qt.Horizontal)

        # ---- Left panel (input) ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(3)

        # Add component widgets
        self.patient_widget = PatientInfoWidget()
        left_layout.addWidget(self.patient_widget)

        self.hospital_search_widget = HospitalSearchWidget()
        self.hospital_search_widget.hospital_selected.connect(self._handle_hospital_selection)
        left_layout.addWidget(self.hospital_search_widget)

        self.transport_widget = TransportOptionsWidget()
        left_layout.addWidget(self.transport_widget)

        self.census_widget = CensusDataWidget()
        self.census_widget.census_updated.connect(self._update_census_data)
        self.census_widget.display_summary.connect(self._display_census_summary)
        # Connect browse button manually to maintain backward compatibility
        self.census_widget.browse_button.clicked.connect(self._browse_census_file)
        left_layout.addWidget(self.census_widget)

        # Submit button
        self.submit_button = QPushButton("Generate Recommendation")
        self.submit_button.setMinimumHeight(40)
        self.submit_button.clicked.connect(self._on_submit)
        left_layout.addWidget(self.submit_button)

        # ---- Right panel (output) ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(3)

        # Add recommendation output widget
        self.recommendation_widget = RecommendationOutputWidget()
        right_layout.addWidget(self.recommendation_widget)

        # Add LLM settings widget
        self.llm_settings_widget = LLMSettingsWidget()
        self.llm_settings_widget.refresh_models.connect(self._refresh_llm_models)
        self.llm_settings_widget.test_connection.connect(self._test_llm_connection)
        self.llm_settings_widget.settings_changed.connect(self._save_settings)
        right_layout.addWidget(self.llm_settings_widget)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])  # Set initial sizes

        main_layout.addWidget(splitter)

        # Set the central widget
        self.setCentralWidget(central_widget)

        # Set up status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def _handle_hospital_selection(self, hospital_data):
        """Handle hospital selection from the search widget."""
        # Implement any additional logic needed when a hospital is selected
        self.statusBar.showMessage(f"Selected hospital: {hospital_data['name']}")

    def _browse_census_file(self):
        """Open file dialog to select a census CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Census CSV File", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.census_file_path = file_path
            self.census_widget.set_file_path(file_path)
            self.statusBar.showMessage(f"Selected census file: {file_path}")

    def _update_census_data(self):
        """Update hospital campuses with current census data."""
        if not self.census_file_path or not os.path.exists(self.census_file_path):
            QMessageBox.warning(
                self,
                "Census Update Error",
                "No census file selected or file does not exist.",
            )
            return

        try:
            # Update census data
            self.statusBar.showMessage("Updating census data...")
            success = update_census(self.census_file_path, self.hospital_file_path)
            
            # Reload updated hospital data from the file
            if success:
                try:
                    with open(self.hospital_file_path, "r") as f:
                        updated_hospitals = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading updated hospital data: {str(e)}")
                    updated_hospitals = None
            else:
                updated_hospitals = None
                
            if updated_hospitals:
                self.hospitals = updated_hospitals
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.last_census_update = timestamp
                self.settings.setValue("census/last_update", timestamp)
                self.census_widget.set_last_update(timestamp)
                
                # Update status display
                status_html = "<p><b>Census data updated successfully.</b></p>"
                status_html += f"<p>Updated at: {timestamp}</p>"
                status_html += f"<p>Updated {len(self.hospitals)} hospitals.</p>"
                self.census_widget.set_status(status_html)
                
                self.statusBar.showMessage("Census data updated successfully")
            else:
                self.census_widget.set_status("<p><b>Error updating census data.</b></p>")
                self.statusBar.showMessage("Error updating census data")
                
        except Exception as e:
            logger.error(f"Error updating census data: {str(e)}")
            self.census_widget.set_status(f"<p><b>Error:</b> {str(e)}</p>")
            self.statusBar.showMessage("Error updating census data")

    def _display_census_summary(self):
        """Display a summary of available beds from hospital campuses."""
        if not self.hospitals:
            QMessageBox.information(
                self, "Census Summary", "No hospital data loaded."
            )
            return

        try:
            summary = "<h3>Current Census Summary</h3>"
            summary += f"<p><b>Last Updated:</b> {self.last_census_update}</p>"
            summary += "<table border='1' cellspacing='0' cellpadding='3'>"
            summary += "<tr><th>Hospital</th><th>General Beds</th><th>ICU Beds</th><th>NICU Beds</th></tr>"
            
            for hospital in self.hospitals:
                summary += f"<tr><td>{hospital.name}</td>"
                summary += f"<td>{hospital.bed_census.available_beds}/{hospital.bed_census.total_beds}</td>"
                summary += f"<td>{hospital.bed_census.icu_beds_available}/{hospital.bed_census.icu_beds_total}</td>"
                summary += f"<td>{hospital.bed_census.nicu_beds_available}/{hospital.bed_census.nicu_beds_total}</td></tr>"
            
            summary += "</table>"
            
            # Show summary in the recommendation output
            self.recommendation_widget.set_recommendation(summary)
            
        except Exception as e:
            logger.error(f"Error displaying census summary: {str(e)}")
            QMessageBox.warning(
                self, "Census Summary Error", f"Error generating summary: {str(e)}"
            )

    def _load_config(self):
        """Load hospital and configuration data."""
        try:
            # Load hospital data
            if os.path.exists(self.hospital_file_path):
                with open(self.hospital_file_path, "r") as f:
                    hospital_data = json.load(f)
                
                self.hospitals = []
                for campus_data in hospital_data:
                    campus = HospitalCampus(
                        campus_id=campus_data.get("campus_id", ""),
                        name=campus_data.get("name", ""),
                        metro_area=MetroArea(campus_data.get("metro_area", "HOUSTON_METRO")),
                        address=campus_data.get("address", ""),
                        location=Location(
                            latitude=campus_data.get("location", {}).get("latitude", 0),
                            longitude=campus_data.get("location", {}).get("longitude", 0),
                        ),
                        bed_census={
                            "total_beds": campus_data.get("bed_census", {}).get("total_beds", 0),
                            "available_beds": campus_data.get("bed_census", {}).get("available_beds", 0),
                            "icu_beds_total": campus_data.get("bed_census", {}).get("icu_beds_total", 0),
                            "icu_beds_available": campus_data.get("bed_census", {}).get("icu_beds_available", 0),
                            "nicu_beds_total": campus_data.get("bed_census", {}).get("nicu_beds_total", 0),
                            "nicu_beds_available": campus_data.get("bed_census", {}).get("nicu_beds_available", 0),
                        },
                        exclusions=campus_data.get("exclusions", []),
                        helipads=[],  # Not implemented yet
                    )
                    self.hospitals.append(campus)
                
                logger.info(f"Loaded {len(self.hospitals)} hospitals")
                self.statusBar.showMessage(f"Loaded {len(self.hospitals)} hospitals")
            else:
                logger.warning(f"Hospital data file not found: {self.hospital_file_path}")
                self.statusBar.showMessage("Hospital data file not found")

            # Load LLM settings
            api_url = self.settings.value("llm/api_url", "http://localhost:1234/v1", str)
            model = self.settings.value("llm/model", "", str)
            
            self.llm_classifier.set_api_url(api_url)
            if model:
                self.llm_classifier.set_model(model)
            
            # Update UI with settings
            self.llm_settings_widget.api_url_input.setText(api_url)
            self._refresh_llm_models()  # This will also update the model dropdown
            
            # Set census last update
            self.census_widget.set_last_update(self.last_census_update)
            self.census_widget.set_file_path(self.census_file_path)

        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self.statusBar.showMessage("Error loading configuration")

    def _save_settings(self):
        """Save application settings."""
        self.settings.setValue("llm/api_url", self.llm_settings_widget.api_url_input.text())
        self.settings.setValue("llm/model", self.llm_settings_widget.model_input.currentText())

    def _refresh_llm_models(self):
        """Refresh the list of available models from LM Studio."""
        try:
            # Update API URL from settings
            api_url = self.llm_settings_widget.api_url_input.text()
            self.llm_classifier.set_api_url(api_url)
            
            # Refresh models
            models = self.llm_classifier.refresh_models()
            
            if models:
                self.llm_settings_widget.set_models(models)
                self.llm_settings_widget.set_status(
                    f"<p><b>Found {len(models)} models:</b></p>"
                    f"<p>{', '.join(models[:5])}{' and more...' if len(models) > 5 else ''}</p>"
                )
                self.statusBar.showMessage(f"Found {len(models)} models")
            else:
                self.llm_settings_widget.set_status(
                    "<p><b>No models found. Is LM Studio running?</b></p>"
                    "<p>Make sure LM Studio is running with the OpenAI API enabled.</p>"
                )
                self.statusBar.showMessage("No models found")
        
        except Exception as e:
            logger.error(f"Error refreshing models: {str(e)}")
            self.llm_settings_widget.set_status(f"<p><b>Error:</b> {str(e)}</p>")
            self.statusBar.showMessage("Error refreshing models")

    def _test_llm_connection(self):
        """Test the connection to the LLM API."""
        try:
            api_url = self.llm_settings_widget.api_url_input.text()
            model = self.llm_settings_widget.model_input.currentText()
            
            self.statusBar.showMessage("Testing LLM connection...")
            self.llm_settings_widget.set_status("<p>Testing connection...</p>")
            
            success, message = self.llm_classifier.test_connection(api_url, model)
            
            if success:
                self.llm_settings_widget.set_status(
                    f"<p><b>Connection successful!</b></p>"
                    f"<p>Model: {model}</p>"
                    f"<p>Message: {message}</p>"
                )
                self.statusBar.showMessage("LLM connection successful")
            else:
                self.llm_settings_widget.set_status(
                    f"<p><b>Connection failed!</b></p>"
                    f"<p>Error: {message}</p>"
                    "<p>Check that LM Studio is running and the API is enabled.</p>"
                )
                self.statusBar.showMessage("LLM connection failed")
        
        except Exception as e:
            logger.error(f"Error testing connection: {str(e)}")
            self.llm_settings_widget.set_status(f"<p><b>Error:</b> {str(e)}</p>")
            self.statusBar.showMessage("Error testing connection")

    def _on_submit(self):
        """Process the form submission and generate recommendations."""
        # Clear previous results
        self.recommendation_widget.clear()
        self.statusBar.showMessage("Generating recommendation...")

        try:
            # Get data from form
            patient_data = self.patient_widget.get_patient_data()
            location_data = self.hospital_search_widget.get_location_data()
            transport_data = self.transport_widget.get_transport_data()
            
            # Validate required inputs
            if not patient_data["clinical_data"]:
                QMessageBox.warning(
                    self, "Missing Data", "Please enter clinical data."
                )
                return

            if not location_data:
                QMessageBox.warning(
                    self, "Missing Data", "Please select a sending facility location."
                )
                return

            # Process clinical data with LLM if available
            clinical_data = patient_data["clinical_data"]
            extracted_data = None
            llm_error = None
            
            try:
                # Get LLM settings
                api_url = self.llm_settings_widget.api_url_input.text()
                model = self.llm_settings_widget.model_input.currentText()
                
                # Update LLM classifier with current settings
                self.llm_classifier.set_api_url(api_url)
                self.llm_classifier.set_model(model)
                
                # Process text with LLM
                extracted_data = self.llm_classifier.process_text(clinical_data)
                
                # Create a serializable copy of the extraction results
                display_data = extracted_data.copy()
                
                # Remove the Recommendation object before serializing
                if "final_recommendation" in display_data:
                    # Store some basic info about the recommendation instead of the full object
                    rec = display_data.pop("final_recommendation")
                    display_data["recommendation_explanation"] = {
                        "recommended_campus_name": rec.recommended_campus_id,
                        "confidence": rec.confidence_score,
                        "key_factors_for_recommendation": rec.explainability_details.get("key_factors_for_recommendation", []) if rec.explainability_details else [],
                        "llm_identified_patient_conditions": rec.explainability_details.get("specialty_services_needed", []) if rec.explainability_details else [],
                        "other_considerations_from_notes": rec.explainability_details.get("other_considerations_from_notes", []) if rec.explainability_details else []
                    }
                
                # Display the raw data
                self.recommendation_widget.set_raw_data(
                    f"<h3>LLM Extraction Results</h3>"
                    f"<pre>{json.dumps(display_data, indent=2)}</pre>"
                )
                
            except Exception as e:
                llm_error = str(e)
                logger.error(f"Error processing with LLM: {llm_error}")
                
                # No fallback - display error to the user and raise the exception
                self.recommendation_widget.set_raw_data(
                    f"<h3>LLM Processing Error</h3>"
                    f"<p><b>Error:</b> {llm_error}</p>"
                    f"<p>The Transfer Center requires a functioning LLM connection to generate recommendations.</p>"
                    f"<p>Please check the LLM connection settings and try again.</p>"
                )
                # Re-raise the exception to prevent further processing
                raise e

            # Collect patient data
            patient = PatientData(
                patient_id=patient_data["patient_id"] or "UNKNOWN",
                clinical_text=clinical_data,
                extracted_data=extracted_data or {},
                care_needs=extracted_data.get("keywords", []) if extracted_data else [],
                care_level=extracted_data.get("suggested_care_level", "General") if extracted_data else "General",
            )

            # Create transfer request
            request = TransferRequest(
                request_id=f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                patient_data=patient,
                sending_location=Location(
                    latitude=location_data["latitude"],
                    longitude=location_data["longitude"],
                ),
                requested_datetime=datetime.now(),
                transport_mode=(
                    TransportMode.GROUND_AMBULANCE
                    if transport_data["transport_mode"] == "Ground"
                    else TransportMode.HELICOPTER
                    if transport_data["transport_mode"] == "Helicopter"
                    else TransportMode.FIXED_WING
                ),
                transport_info={
                    "type": transport_data["transport_type"],
                    "mode": transport_data["transport_mode"],
                    "departure_time": transport_data["departure_time"],
                },
            )

            # Get care levels from extracted data
            care_levels = []
            if extracted_data and "suggested_care_level" in extracted_data:
                care_level = extracted_data["suggested_care_level"]
                if care_level == "NICU":
                    care_levels = ["NICU"]
                elif care_level == "PICU" or care_level == "ICU":
                    care_levels = ["PICU", "ICU"]
                else:
                    care_levels = ["General"]

            # Get transport time estimates
            transport_modes = [
                TransportMode.GROUND_AMBULANCE,
                TransportMode.HELICOPTER,
                TransportMode.FIXED_WING,
            ]
            
            transport_estimates = self.transport_estimator.estimate_transport_times(
                request.sending_location,
                self.hospitals,
                transport_modes,
                transport_type=request.transport_info["type"],
                kc_mode=request.transport_info["mode"].lower(),
            )

            # Process with LLM and get recommendation
            if not extracted_data:
                raise ValueError("Clinical data extraction failed. Check LLM configuration.")
                
            # The LLM recommendation should already be a proper Recommendation object
            # from the changes we made to the LLMClassifier.process_text method and
            # RecommendationGenerator.generate_recommendation method
            recommendation = extracted_data.get("final_recommendation")
            
            if not recommendation:
                raise ValueError("LLM recommendation required but not available. Check logs for details.")
                
            # Ensure it's a proper Recommendation object
            if not isinstance(recommendation, Recommendation):
                raise ValueError(f"Expected Recommendation object but got {type(recommendation).__name__}")
                
            # Set the transfer request ID to match the current request
            recommendation.transfer_request_id = request.request_id
            
            # Log the recommendation details
            logger.info(f"Using LLM recommendation for {recommendation.recommended_campus_id} with confidence {recommendation.confidence_score}%")

            # Display recommendation
            self._display_recommendation(recommendation)
            self.statusBar.showMessage("Recommendation generated successfully")

        except Exception as e:
            logger.error(f"Error generating recommendation: {str(e)}")
            self.statusBar.showMessage("Error generating recommendation")
            self.recommendation_widget.set_recommendation(
                f"<h3>Error Generating Recommendation</h3>"
                f"<p>{str(e)}</p>"
                f"<p>Check the application logs for more details.</p>"
            )

    def _display_recommendation(self, recommendation: Optional[Recommendation]):
        """Display the recommendation results."""
        if not recommendation:
            self.recommendation_widget.set_recommendation(
                "<h3>No Recommendation Available</h3>"
                "<p>No suitable hospital was found based on the criteria.</p>"
                "<p>Consider updating the census data or modifying the patient details.</p>"
            )
            return
            
        # Check if this is an LLM-generated recommendation by checking if the recommended_campus_id
        # is one of the known hospital IDs or if it's a full hospital name
        known_campus_ids = set(h.campus_id for h in self.hospitals)
        is_llm_recommendation = recommendation.recommended_campus_id not in known_campus_ids
        
        if is_llm_recommendation:
            # Get campus name from explainability details if available
            campus_name = "Unknown Campus"
            if recommendation.explainability_details and "recommended_campus_name" in recommendation.explainability_details:
                campus_name = recommendation.explainability_details["recommended_campus_name"]
            else:
                campus_name = recommendation.recommended_campus_id
                
            # Display LLM recommendation
            recommendation_html = f"<h2>Recommendation: {campus_name}</h2>"
            recommendation_html += f"<p><b>Confidence:</b> {recommendation.confidence_score:.1f}%</p>"
            recommendation_html += f"<p><b>Reason:</b> {recommendation.reason}</p>"
            
            # Add considerations and key factors
            if recommendation.explainability_details:
                details = recommendation.explainability_details
                
                # Key factors
                if "key_factors_for_recommendation" in details and details["key_factors_for_recommendation"]:
                    recommendation_html += "<h3>Key Factors</h3><ul>"
                    for factor in details["key_factors_for_recommendation"]:
                        recommendation_html += f"<li>{factor}</li>"
                    recommendation_html += "</ul>"
                
                # Excluded campuses and reasons
                if "excluded_campuses" in details and details["excluded_campuses"]:
                    recommendation_html += "<h3>Why Other Campuses Were Not Selected</h3><ul>"
                    for campus in details["excluded_campuses"]:
                        name = campus.get("name", "Unknown Campus")
                        reason = campus.get("reason", "No reason provided")
                        recommendation_html += f"<li><b>{name}:</b> {reason}</li>"
                    recommendation_html += "</ul>"
                
                # Considerations/notes
                if "other_considerations_from_notes" in details and details["other_considerations_from_notes"]:
                    recommendation_html += "<h3>Considerations</h3><ul>"
                    for note in details["other_considerations_from_notes"]:
                        recommendation_html += f"<li>{note}</li>"
                    recommendation_html += "</ul>"
            
            # Add notes if available
            if recommendation.notes:
                recommendation_html += "<h3>Required Resources</h3><ul>"
                for note in recommendation.notes:
                    recommendation_html += f"<li>{note}</li>"
                recommendation_html += "</ul>"
                
        else:
            # Find the recommended hospital (for traditional recommendations)
            recommended_hospital = next(
                (
                    h
                    for h in self.hospitals
                    if h.campus_id == recommendation.recommended_campus_id
                ),
                None,
            )
            hospital_name = (
                recommended_hospital.name
                if recommended_hospital
                else recommendation.recommended_campus_id
            )
    
            # Display main recommendation
            recommendation_html = f"<h2>Recommendation: {hospital_name}</h2>"
            recommendation_html += f"<p><b>Confidence:</b> {recommendation.confidence_score:.1f}%</p>"
            recommendation_html += f"<p><b>Reason:</b> {recommendation.reason}</p>"
    
            if recommended_hospital:
                recommendation_html += "<h3>Hospital Details</h3>"
                recommendation_html += f"<p><b>Location:</b> {recommended_hospital.address}</p>"
                recommendation_html += "<p><b>Bed Availability:</b></p><ul>"
                recommendation_html += (
                    f"<li>General: {recommended_hospital.bed_census.available_beds}/"
                    f"{recommended_hospital.bed_census.total_beds}</li>"
                )
                recommendation_html += (
                    f"<li>ICU: {recommended_hospital.bed_census.icu_beds_available}/"
                    f"{recommended_hospital.bed_census.icu_beds_total}</li>"
                )
                recommendation_html += (
                    f"<li>NICU: {recommended_hospital.bed_census.nicu_beds_available}/"
                    f"{recommended_hospital.bed_census.nicu_beds_total}</li>"
                )
                recommendation_html += "</ul>"

        # Display decision notes
        if recommendation.notes:
            recommendation_html += "<h3>Decision Notes</h3><ul>"
            for note in recommendation.notes:
                recommendation_html += f"<li>{note}</li>"
            recommendation_html += "</ul>"

        # Set recommendation content
        self.recommendation_widget.set_recommendation(recommendation_html)

        # Display explainability details in the explanation tab
        if recommendation.explainability_details:
            explanation_html = "<h3>Recommendation Explanation</h3>"

            # Format the explainability details
            if isinstance(recommendation.explainability_details, dict):
                for category, details in recommendation.explainability_details.items():
                    explanation_html += f"<h4>{category.replace('_', ' ').title()}</h4>"

                    if isinstance(details, dict):
                        explanation_html += "<ul>"
                        for k, v in details.items():
                            explanation_html += f"<li><b>{k}:</b> {v}</li>"
                        explanation_html += "</ul>"
                    elif isinstance(details, list):
                        explanation_html += "<ul>"
                        for item in details:
                            explanation_html += f"<li>{item}</li>"
                        explanation_html += "</ul>"
                    else:
                        explanation_html += f"<p>{details}</p>"
            else:
                explanation_html += f"<p>{str(recommendation.explainability_details)}</p>"

            # Set explanation content
            self.recommendation_widget.set_explanation(explanation_html)


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Create and show the main window
    main_window = TransferCenterMainWindow()
    main_window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

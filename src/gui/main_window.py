"""
Main window for the Transfer Center GUI application.

This module implements the main application window using PyQt5.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from PyQt5.QtCore import QSettings, QSize, QStringListModel, Qt, QTime, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QTextCursor
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
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
)
from src.gui.hospital_search import HospitalSearch
from src.gui.llm_integration import LLMClassifier
from src.gui.transport_time_estimator import TransportTimeEstimator
from src.utils.census_updater import update_census

logger = logging.getLogger(__name__)


class TransferCenterMainWindow(QMainWindow):
    """Main window for the Transfer Center GUI application."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Texas Children's Hospital - Transfer Center")
        self.setMinimumSize(1200, 800)  # Back to normal size

        # Use a more compact app-wide font
        app_font = QFont()
        app_font.setPointSize(9)  # Smaller text throughout the application
        QApplication.setFont(app_font)

        # State variables
        self.hospitals: List[HospitalCampus] = []
        self.weather_data: Optional[WeatherData] = None
        self.llm_classifier = LLMClassifier()
        self.transport_estimator = TransportTimeEstimator()
        self.hospital_search = HospitalSearch()
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

        # Create splitter for adjustable sections - more compact
        splitter = QSplitter(Qt.Horizontal)

        # ---- Left panel (input) ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)  # Smaller margins
        left_layout.setSpacing(3)  # Smaller spacing between elements

        # Patient Information Group - more compact
        patient_group = QGroupBox("Patient Information")
        patient_layout = QFormLayout()
        patient_layout.setContentsMargins(5, 5, 5, 5)  # Smaller margins
        patient_layout.setVerticalSpacing(2)  # Minimal vertical spacing
        patient_layout.setHorizontalSpacing(5)  # Minimal horizontal spacing

        self.patient_id_input = QLineEdit()
        self.patient_id_input.setPlaceholderText("Enter patient ID")

        self.clinical_data_input = QTextEdit()
        self.clinical_data_input.setPlaceholderText(
            "Enter or paste clinical data here..."
        )
        self.clinical_data_input.setMinimumHeight(150)

        # Human suggestions group
        suggestions_group = QGroupBox("Clinical Suggestions")
        suggestions_layout = QVBoxLayout()

        suggestion_form = QFormLayout()
        self.icu_checkbox = QCheckBox("May need ICU")
        self.picu_checkbox = QCheckBox("May need PICU")
        self.nicu_checkbox = QCheckBox("May need NICU")

        location_hbox = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItems(
            ["No preference", "Prefers Houston", "Prefers Austin"]
        )
        location_hbox.addWidget(self.location_combo)

        suggestion_form.addRow("Care Level:", self.icu_checkbox)
        suggestion_form.addRow("", self.picu_checkbox)
        suggestion_form.addRow("", self.nicu_checkbox)
        suggestion_form.addRow("Location Preference:", location_hbox)

        # Additional suggestions
        self.additional_suggestions = QTextEdit()
        self.additional_suggestions.setPlaceholderText(
            "Enter any additional suggestions or notes..."
        )
        self.additional_suggestions.setMaximumHeight(80)

        suggestions_layout.addLayout(suggestion_form)
        suggestions_layout.addWidget(QLabel("Additional Notes:"))
        suggestions_layout.addWidget(self.additional_suggestions)
        suggestions_group.setLayout(suggestions_layout)

        # Transport Information Group
        transport_group = QGroupBox("Transport Information")
        transport_layout = QVBoxLayout()

        # Transport type section with fixed-size elements to prevent layout shifts
        transport_type_form = QFormLayout()
        transport_type_form.setContentsMargins(0, 0, 0, 0)  # Reduce margins
        transport_type_form.setSpacing(5)  # Reduce vertical spacing

        # Make combo box wider and set a minimum width
        self.transport_combo = QComboBox()
        self.transport_combo.setMinimumWidth(200)
        self.transport_combo.setMaximumHeight(25)  # Limit height to save vertical space
        self.transport_combo.addItems(
            ["POV (Private Vehicle)", "Local EMS", "Kangaroo Crew"]
        )

        # Transport mode sub-group that appears when Kangaroo Crew is selected
        # Create a fixed-size container to prevent layout shifts
        kc_container = QWidget()
        kc_container.setFixedHeight(40)  # Fixed height prevents layout shifts

        self.kc_mode_group = QGroupBox("")
        kc_mode_layout = QHBoxLayout()
        kc_mode_layout.setContentsMargins(0, 0, 0, 0)  # Minimize padding
        kc_mode_layout.setSpacing(5)  # Reduce spacing between options

        # Make radio buttons more compact
        self.kc_ground = QRadioButton("Ground")
        self.kc_rotor = QRadioButton("Helicopter")
        self.kc_fixed = QRadioButton("Fixed Wing")
        self.kc_ground.setChecked(True)

        # Force buttons to use less space
        for btn in [self.kc_ground, self.kc_rotor, self.kc_fixed]:
            btn.setMaximumHeight(20)
            font = btn.font()
            font.setPointSize(10)  # Smaller text
            btn.setFont(font)

        kc_mode_layout.addWidget(QLabel("KC Mode:"))
        kc_mode_layout.addWidget(self.kc_ground)
        kc_mode_layout.addWidget(self.kc_rotor)
        kc_mode_layout.addWidget(self.kc_fixed)
        self.kc_mode_group.setLayout(kc_mode_layout)

        # Add to the fixed container
        kc_container_layout = QVBoxLayout(kc_container)
        kc_container_layout.setContentsMargins(0, 0, 0, 0)
        kc_container_layout.addWidget(self.kc_mode_group)

        # Start with the container visible but the group hidden
        self.kc_mode_group.setVisible(False)

        # Connect transport combo to show/hide KC mode group
        self.transport_combo.currentIndexChanged.connect(self._update_transport_ui)

        # ETA Group
        eta_form = QFormLayout()
        self.has_eta_checkbox = QCheckBox("Specify ETA")
        self.eta_time = QTimeEdit()
        self.eta_time.setTime(
            QTime.currentTime().addSecs(3600)
        )  # Default to 1 hour from now
        self.eta_time.setEnabled(False)
        self.has_eta_checkbox.toggled.connect(self.eta_time.setEnabled)

        eta_form.addRow("", self.has_eta_checkbox)
        eta_form.addRow("Estimated Time of Arrival:", self.eta_time)

        # Sending Facility Information with Hospital Search
        sending_form = QFormLayout()

        # Hospital search layout - ultra compact to fit on screen
        hospital_search_layout = QVBoxLayout()
        hospital_search_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        hospital_search_layout.setSpacing(2)  # Minimal spacing
        search_input_layout = QHBoxLayout()
        search_input_layout.setContentsMargins(0, 0, 0, 0)  # No margins

        # Much smaller fixed height for the search area
        hospital_search_widget = QWidget()
        hospital_search_widget.setFixedHeight(
            140
        )  # Significantly smaller but still functional

        # Make the sending facility line edit show the full selected hospital name
        self.sending_facility = QLineEdit()
        self.sending_facility.setMinimumWidth(
            300
        )  # Ensure enough width for longer hospital names
        self.sending_facility.setPlaceholderText(
            "Enter sending facility name or address"
        )

        # Fixed width search button
        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedWidth(80)  # Prevents the button from changing width
        self.search_btn.clicked.connect(self._search_hospital)

        search_input_layout.addWidget(
            self.sending_facility, 4
        )  # Give more space to the input field
        search_input_layout.addWidget(self.search_btn, 1)  # Fixed ratio for layout

        # Results list with much smaller fixed size
        self.hospital_results = QListWidget()
        self.hospital_results.setFixedHeight(80)  # Much shorter but still functional
        self.hospital_results.setMaximumWidth(
            400
        )  # Limit width to prevent horizontal expansion
        self.hospital_results.itemClicked.connect(self._select_hospital)
        self.hospital_results.setVisible(False)  # Hide until search is performed

        # Make list items more compact
        self.hospital_results.setStyleSheet("QListWidget::item { padding: 1px; }")

        # Apply layouts to the fixed-size widget
        hospital_search_layout.addLayout(search_input_layout)
        hospital_search_layout.addWidget(self.hospital_results)
        hospital_search_widget.setLayout(hospital_search_layout)

        # Keep the coordinate fields as hidden variables but don't display them in
        # the UI
        self.lat_input = QLineEdit()
        self.lat_input.setText("29.7604")  # Default Houston area
        self.lat_input.setVisible(False)  # Completely hide from UI

        self.lon_input = QLineEdit()
        self.lon_input.setText("-95.3698")  # Default Houston area
        self.lon_input.setVisible(False)  # Completely hide from UI

        # Add only the hospital search widget to the form (coordinates are hidden)
        sending_form.addRow("Sending Facility:", hospital_search_widget)

        # Add all sections to transport layout
        transport_type_form.addRow("Transport Type:", self.transport_combo)
        transport_layout.addLayout(transport_type_form)
        transport_layout.addWidget(
            kc_container
        )  # Add the fixed-size container instead of the group directly
        transport_layout.addLayout(eta_form)
        transport_layout.addLayout(sending_form)
        transport_group.setLayout(transport_layout)

        # Add components to patient layout
        patient_layout.addRow("Patient ID:", self.patient_id_input)
        patient_layout.addRow("Clinical Data:", self.clinical_data_input)
        patient_group.setLayout(patient_layout)

        # Add groups to left layout
        left_layout.addWidget(patient_group)
        left_layout.addWidget(suggestions_group)
        left_layout.addWidget(transport_group)

        # Submit button
        self.submit_button = QPushButton("Generate Recommendation")
        self.submit_button.setMinimumHeight(50)
        self.submit_button.clicked.connect(self._on_submit)
        left_layout.addWidget(self.submit_button)

        # ---- Right panel (output) ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Results Tab Widget
        results_tabs = QTabWidget()

        # Recommendation tab
        recommendation_tab = QWidget()
        recommendation_layout = QVBoxLayout(recommendation_tab)

        self.recommendation_output = QTextEdit()
        self.recommendation_output.setReadOnly(True)
        self.recommendation_output.setStyleSheet(
            "background-color: #f5f5f5; color: #333333; font-size: 10pt;"
        )

        recommendation_layout.addWidget(self.recommendation_output)
        results_tabs.addTab(recommendation_tab, "Recommendation")

        # Explanation tab
        explanation_tab = QWidget()
        explanation_layout = QVBoxLayout(explanation_tab)

        self.explanation_output = QTextEdit()
        self.explanation_output.setReadOnly(True)
        self.explanation_output.setStyleSheet(
            "background-color: #f5f5f5; color: #333333; font-size: 10pt;"
        )

        explanation_layout.addWidget(self.explanation_output)
        results_tabs.addTab(explanation_tab, "Explanation")

        # LLM Classification tab
        llm_tab = QWidget()
        llm_layout = QVBoxLayout(llm_tab)

        self.llm_output = QTextEdit()
        self.llm_output.setReadOnly(True)
        self.llm_output.setStyleSheet(
            "background-color: #f5f5f5; color: #333333; font-size: 10pt;"
        )

        llm_config_box = QGroupBox("LLM Configuration")
        llm_config_layout = QFormLayout()

        self.llm_url_input = QLineEdit("http://localhost:1234/v1")
        self.llm_url_input.setPlaceholderText("LM Studio API URL")

        self.llm_model_combo = QComboBox()
        self.llm_model_combo.addItem(
            "Loading models..."
        )  # Placeholder until models are loaded

        # Add a refresh models button
        self.refresh_models_button = QPushButton("Refresh Models")
        self.refresh_models_button.clicked.connect(self._refresh_llm_models)

        self.llm_test_button = QPushButton("Test LLM Connection")
        self.llm_test_button.clicked.connect(self._test_llm_connection)

        llm_config_layout.addRow("LM Studio API URL:", self.llm_url_input)
        llm_config_layout.addRow("Model:", self.llm_model_combo)
        refresh_button_layout = QHBoxLayout()
        refresh_button_layout.addWidget(self.refresh_models_button)
        refresh_button_layout.addWidget(self.llm_test_button)
        llm_config_layout.addRow("", refresh_button_layout)
        llm_config_box.setLayout(llm_config_layout)

        llm_layout.addWidget(llm_config_box)
        llm_layout.addWidget(QLabel("Classification Results:"))
        llm_layout.addWidget(self.llm_output)

        results_tabs.addTab(llm_tab, "LLM Classification")

        # Hospital Census tab
        census_tab = QWidget()
        census_layout = QVBoxLayout(census_tab)

        census_box = QGroupBox("Hospital Census Management")
        census_form_layout = QFormLayout()

        # Show when census was last updated
        self.census_last_updated_label = QLabel(
            f"Last updated: {self.last_census_update}"
        )
        census_form_layout.addRow("Census Status:", self.census_last_updated_label)

        # Add census file path display with browse button
        census_path_layout = QHBoxLayout()
        self.census_path_display = QLineEdit(self.census_file_path)
        self.census_path_display.setReadOnly(True)
        browse_census_btn = QPushButton("Browse...")
        browse_census_btn.clicked.connect(self._browse_census_file)
        census_path_layout.addWidget(self.census_path_display)
        census_path_layout.addWidget(browse_census_btn)
        census_form_layout.addRow("Census File:", census_path_layout)

        # Add refresh button
        self.refresh_census_btn = QPushButton("Refresh Bed Census")
        self.refresh_census_btn.setToolTip("Update hospital bed availability data")
        self.refresh_census_btn.clicked.connect(self._update_census_data)
        census_form_layout.addRow("", self.refresh_census_btn)

        # Area to display census data summary
        self.census_summary = QTextEdit()
        self.census_summary.setReadOnly(True)
        census_form_layout.addRow("Available Beds Summary:", self.census_summary)

        census_box.setLayout(census_form_layout)
        census_layout.addWidget(census_box)

        results_tabs.addTab(census_tab, "Hospital Census")

        # Transport Analysis tab
        transport_tab = QWidget()
        transport_layout = QVBoxLayout(transport_tab)

        self.transport_output = QTextEdit()
        self.transport_output.setReadOnly(True)
        self.transport_output.setStyleSheet(
            "background-color: #f5f5f5; color: #333333; font-size: 10pt;"
        )

        transport_layout.addWidget(self.transport_output)
        results_tabs.addTab(transport_tab, "Transport Analysis")

        # Add components to right layout
        right_layout.addWidget(results_tabs)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])

        # Add splitter to main layout
        main_layout.addWidget(splitter)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Status bar with census information
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.census_status = QLabel(f"Census last updated: {self.last_census_update}")
        self.statusBar.addPermanentWidget(self.census_status)

        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        tools_menu = menubar.addMenu("Tools")

        # File menu actions
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu actions
        update_census_action = QAction("Update Census Data", self)
        update_census_action.triggered.connect(self._update_census_data)
        tools_menu.addAction(update_census_action)

    def _update_transport_ui(self, index):
        """Update transport UI elements based on selected transport type."""
        # Show the Kangaroo Crew mode options only when Kangaroo Crew is selected
        # (index 2)
        self.kc_mode_group.setVisible(index == 2)

    @pyqtSlot()
    def _search_hospital(self):
        """Search for hospitals based on user input."""
        query = self.sending_facility.text().strip()
        if not query:
            QMessageBox.warning(
                self,
                "Search Error",
                "Please enter a hospital name or address to search",
            )
            return

        # Clear previous results
        self.hospital_results.clear()

        # Perform search
        results = self.hospital_search.search_hospitals(query)

        if not results:
            # Try geocoding as a fallback
            lat, lon = self.hospital_search.geocode_address(query)
            if lat and lon:
                # Add as a generic result
                self.hospital_results.addItem(f"Location: {query}")
                # Store coordinates for later use
                self.hospital_results.item(0).setData(
                    Qt.UserRole,
                    {
                        "name": query,
                        "latitude": lat,
                        "longitude": lon,
                        "address": query,
                        "campus_id": "",
                    },
                )
            else:
                self.hospital_results.addItem("No results found")
                self.hospital_results.item(0).setForeground(QColor("red"))
        else:
            # Add results to list
            for hospital in results:
                item = QListWidgetItem(f"{hospital['name']}")
                item.setData(Qt.UserRole, hospital)
                self.hospital_results.addItem(item)

        # Show results
        self.hospital_results.setVisible(True)

    @pyqtSlot(QListWidgetItem)
    def _select_hospital(self, item):
        """Handle hospital selection from search results."""
        data = item.data(Qt.UserRole)
        if isinstance(data, dict):
            # Update the facility name
            self.sending_facility.setText(data["name"])

            # Update coordinates
            self.lat_input.setText(str(data["latitude"]))
            self.lon_input.setText(str(data["longitude"]))

            # Hide results list
            self.hospital_results.setVisible(False)

    @pyqtSlot()
    def _browse_census_file(self):
        """Open file dialog to select a census CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Census CSV File",
            os.path.dirname(self.census_file_path),
            "CSV Files (*.csv);;All Files (*)",
        )

        if file_path:
            self.census_file_path = file_path
            self.census_path_display.setText(file_path)
            logger.info(f"Census file path updated to: {file_path}")

    def _update_census_data(self):
        """Update hospital campuses with current census data."""
        try:
            # Ensure census file exists
            if not os.path.exists(self.census_file_path):
                QMessageBox.warning(
                    self,
                    "Census File Missing",
                    f"Census file not found at: {self.census_file_path}\n\n"
                    "Please ensure the file exists or select a new file.",
                )
                return

            # Update hospital campuses with current census data
            update_success = update_census(
                self.census_file_path, self.hospital_file_path
            )

            if update_success:
                # Reload hospital data
                with open(self.hospital_file_path, "r") as f:
                    hospitals_data = json.load(f)
                    self.hospitals = [HospitalCampus(**h) for h in hospitals_data]

                # Update last update time
                self.last_census_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.settings.setValue("census/last_update", self.last_census_update)
                self.census_last_updated_label.setText(
                    f"Last updated: {self.last_census_update}"
                )

                # Display census summary
                self._display_census_summary()

                QMessageBox.information(
                    self,
                    "Census Update",
                    "Hospital campus data successfully updated with current census.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Census Update Failed",
                    "Failed to update hospital campus data. Check the log for details.",
                )
        except Exception as e:
            logger.error(f"Error updating census data: {str(e)}")
            QMessageBox.critical(
                self,
                "Census Update Error",
                f"An error occurred while updating census data: {str(e)}",
            )

    def _display_census_summary(self):
        """Display a summary of available beds from hospital campuses."""
        if not self.hospitals:
            self.census_summary.setPlainText("No hospital data loaded.")
            return

        summary_text = """<h3>Hospital Bed Availability Summary</h3>
<table border='1' cellpadding='4'>
<tr>
  <th>Campus</th>
  <th>General Beds</th>
  <th>ICU Beds</th>
  <th>NICU Beds</th>
  <th>Specialized Units</th>
</tr>"""

        for hospital in self.hospitals:
            specializations = (
                ", ".join(hospital.specializations)
                if hospital.specializations
                else "None"
            )
            summary_text += f"""
<tr>
  <td>{hospital.name}</td>
  <td>{hospital.available_beds.general if hospital.available_beds and hospital.available_beds.general is not None else 'N/A'}</td>
  <td>{hospital.available_beds.icu if hospital.available_beds and hospital.available_beds.icu is not None else 'N/A'}</td>
  <td>{hospital.available_beds.nicu if hospital.available_beds and hospital.available_beds.nicu is not None else 'N/A'}</td>
  <td>{specializations}</td>
</tr>"""

        summary_text += "</table>"

        # Display the formatted HTML table
        self.census_summary.setHtml(summary_text)
        logger.info("Census summary updated in UI")

    def _load_config(self):
        """Load hospital and configuration data."""
        # Attempt to update census data on startup
        try:
            # Check if census file exists and log detailed information
            if os.path.exists(self.census_file_path):
                logger.info(f"Census file found at {self.census_file_path}")
                print(f"DEBUG: Census file found at {self.census_file_path}")

                # Force update of census data on startup
                update_success = update_census(
                    self.census_file_path, self.hospital_file_path
                )

                if update_success:
                    self.last_census_update = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    self.settings.setValue(
                        "census/last_update", self.last_census_update
                    )
                    logger.info(
                        f"Census data updated on startup: {self.last_census_update}"
                    )
                    print(f"DEBUG: Census data successfully updated on startup")
                else:
                    logger.warning("Census update failed during startup")
                    print("DEBUG: Census update failed during startup")
            else:
                logger.warning(f"Census file NOT found at {self.census_file_path}")
                print(f"DEBUG: Census file NOT found at {self.census_file_path}")
        except Exception as e:
            logger.error(f"Error updating census on startup: {str(e)}")
            print(f"DEBUG: Error updating census on startup: {str(e)}")

        # Load hospital data AFTER census update
        try:
            logger.info(f"Loading hospital data from {self.hospital_file_path}")
            print(f"DEBUG: Loading hospital data from {self.hospital_file_path}")

            with open(self.hospital_file_path, "r") as f:
                hospitals_data = json.load(f)
                self.hospitals = [HospitalCampus(**h) for h in hospitals_data]

            # Log some info about the loaded hospitals to verify census data was applied
            for hospital in self.hospitals:
                if hospital.campus_id == "TCH_NORTH_AUSTIN":
                    logger.info(
                        f"Austin hospital loaded: {
                            hospital.name} with {
                            hospital.bed_census.available_beds} general beds, {
                            hospital.bed_census.icu_beds_available} ICU beds"
                    )
                    print(
                        f"DEBUG: Austin hospital has {
                            hospital.bed_census.available_beds} general beds, {
                            hospital.bed_census.icu_beds_available} ICU beds"
                    )
        except Exception as e:
            logger.error(f"Error loading hospital data: {str(e)}")
            print(f"DEBUG: Error loading hospital data: {str(e)}")
            self.hospitals = []

        # Load weather data
        weather_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "sample_weather_conditions.json",
        )
        try:
            with open(weather_file, "r") as f:
                weather_data = json.load(f)
                self.weather_data = WeatherData(**weather_data)
        except Exception as e:
            logger.error(f"Error loading weather data: {str(e)}")
            self.weather_data = None

            # Load saved settings
            api_url = self.settings.value("llm/api_url", "http://localhost:1234/v1")
            model_name = self.settings.value("llm/model_name", "")

            self.llm_url_input.setText(api_url)

            # Initialize the LLM classifier with saved settings
            self.llm_classifier.set_api_url(api_url)

            # Try to refresh models
            self._refresh_llm_models()

            # Set the saved model if available
            if model_name:
                index = self.llm_model_combo.findText(model_name)
                if index >= 0:
                    self.llm_model_combo.setCurrentIndex(index)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Configuration Error",
                f"Error loading configuration: {str(e)}\n\n"
                "The application will continue with default settings.",
            )

    def _save_settings(self):
        """Save application settings."""
        self.settings.setValue("llm/api_url", self.llm_url_input.text())
        self.settings.setValue("llm/model_name", self.llm_model_combo.currentText())

    @pyqtSlot()
    def _refresh_llm_models(self):
        """Refresh the list of available models from LM Studio."""
        api_url = self.llm_url_input.text()
        self.llm_classifier.set_api_url(api_url)

        # Clear and add a loading indicator
        self.llm_model_combo.clear()
        self.llm_model_combo.addItem("Loading models...")

        try:
            # Get available models
            available_models = self.llm_classifier.refresh_models()

            # Update the combo box
            self.llm_model_combo.clear()
            if available_models:
                self.llm_model_combo.addItems(available_models)
                self.llm_model_combo.addItem("[Custom Model]")

                # Try to restore previously selected model
                model_name = self.settings.value("llm/model_name", "")
                if model_name:
                    index = self.llm_model_combo.findText(model_name)
                    if index >= 0:
                        self.llm_model_combo.setCurrentIndex(index)
                    else:
                        self.llm_model_combo.setCurrentIndex(0)  # Set to first model
                else:
                    self.llm_model_combo.setCurrentIndex(0)  # Set to first model
            else:
                # If no models found, add some default suggestions
                self.llm_model_combo.addItems(
                    [
                        "No models found - suggestions:",
                        "llama-3",
                        "mistral",
                        "gemma",
                        "phi-2",
                        "biomistral-7b",
                        "[Custom Model]",
                    ]
                )
                QMessageBox.warning(
                    self,
                    "Models Not Found",
                    "Could not retrieve models from LM Studio. Check if the server is running.",
                )
        except Exception as e:
            self.llm_model_combo.clear()
            self.llm_model_combo.addItem("Error loading models")
            self.llm_model_combo.addItem("[Custom Model]")
            QMessageBox.warning(
                self, "Model Loading Error", f"Error loading models: {str(e)}"
            )

    @pyqtSlot()
    def _test_llm_connection(self):
        """Test the connection to the LLM API."""
        api_url = self.llm_url_input.text()
        model = self.llm_model_combo.currentText()

        # Skip testing if no valid model is selected
        if model in [
            "Loading models...",
            "Error loading models",
            "No models found - suggestions:",
        ]:
            QMessageBox.warning(
                self,
                "Invalid Model",
                "Please select a valid model or refresh the model list first.",
            )
            return

        try:
            # Show a message that we're testing
            self.llm_output.clear()
            self.llm_output.append(
                f"<p>Testing connection to {api_url} with model: {model}...</p>"
            )
            QApplication.processEvents()  # Update the UI

            # Test connection (now returns tuple of success and message)
            success, message = self.llm_classifier.test_connection(api_url, model)

            if success:
                QMessageBox.information(
                    self,
                    "Connection Successful",
                    f"Successfully connected to LM Studio API using model: {model}",
                )
                # Save the working model
                self.settings.setValue("llm/model_name", model)
                self.llm_output.append(
                    f"<p style='color:green'><b>Connection successful!</b></p>"
                )
                self.llm_output.append(f"<p>Response: {message}</p>")
            else:
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    f"Failed to connect to LM Studio API: {message}",
                )
                self.llm_output.append(
                    f"<p style='color:red'><b>Connection failed!</b></p>"
                )
                self.llm_output.append(f"<p>Error: {message}</p>")
                self.llm_output.append(f"<p>Troubleshooting tips:</p>")
                self.llm_output.append("<ul>")
                self.llm_output.append(
                    "<li>Make sure LM Studio is running and the server is started</li>"
                )
                self.llm_output.append(
                    "<li>Check that the URL format is correct (usually http://localhost:1234/v1)</li>"
                )
                self.llm_output.append(
                    "<li>Verify the model is loaded in LM Studio</li>"
                )
                self.llm_output.append("<li>Try refreshing the model list</li>")
                self.llm_output.append("</ul>")
        except Exception as e:
            QMessageBox.critical(
                self, "Connection Error", f"Error connecting to LM Studio API: {str(e)}"
            )
            self.llm_output.append(f"<p style='color:red'><b>Connection error!</b></p>")
            self.llm_output.append(f"<p>Exception: {str(e)}</p>")

    @pyqtSlot()
    def _on_submit(self):
        """Process the form submission and generate recommendations."""
        # Validate inputs
        if not self.patient_id_input.text().strip():
            QMessageBox.warning(self, "Input Error", "Please enter a patient ID")
            return

        if not self.clinical_data_input.toPlainText().strip():
            QMessageBox.warning(self, "Input Error", "Please enter clinical data")
            return

        if not self.sending_facility.text().strip():
            QMessageBox.warning(
                self, "Input Error", "Please enter sending facility name"
            )
            return

        # Check if we have a valid model selected
        current_model = self.llm_model_combo.currentText()
        if current_model in [
            "Loading models...",
            "Error loading models",
            "No models found - suggestions:",
        ]:
            # Try to refresh models first
            self._refresh_llm_models()

            # Check if we now have valid models
            if self.llm_model_combo.currentText() in [
                "Loading models...",
                "Error loading models",
                "No models found - suggestions:",
            ]:
                response = QMessageBox.question(
                    self,
                    "Model Issue",
                    "No valid model is selected. Continue with basic processing (no LLM)?",
                )
                if response != QMessageBox.Yes:
                    return

        # 1. Process clinical data with LLM
        clinical_text = self.clinical_data_input.toPlainText()
        self.llm_output.clear()
        self.llm_output.append("Processing clinical data with LLM classifier...")

        # Update LLM settings
        self.llm_classifier.set_api_url(self.llm_url_input.text())
        model_name = self.llm_model_combo.currentText()
        if model_name not in [
            "Loading models...",
            "Error loading models",
            "No models found - suggestions:",
        ]:
            self.llm_classifier.set_model(model_name)

        # Convert coordinates to float
        try:
            lat = float(self.lat_input.text())
            lon = float(self.lon_input.text())
        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                "Invalid coordinates. Please select a valid location.",
            )
            return

        # Process with LLM
        llm_results = self.llm_classifier.process_text(
            clinical_text, human_suggestions=self._get_human_suggestions()
        )

        # Display LLM results
        self.llm_output.clear()
        self.llm_output.append(f"<h3>LLM Classification Results</h3>")
        self.llm_output.append(
            f"<p><b>Chief Complaint:</b> {llm_results.get('chief_complaint', 'Not identified')}</p>"
        )
        self.llm_output.append(
            f"<p><b>Clinical History:</b> {llm_results.get('clinical_history', 'Not identified')}</p>"
        )

        if "vital_signs" in llm_results and llm_results["vital_signs"]:
            self.llm_output.append("<p><b>Extracted Vital Signs:</b></p><ul>")
            for k, v in llm_results["vital_signs"].items():
                self.llm_output.append(f"<li>{k}: {v}</li>")
            self.llm_output.append("</ul>")

        if "keywords" in llm_results and llm_results["keywords"]:
            self.llm_output.append("<p><b>Identified Keywords:</b></p>")
            self.llm_output.append("<p>" + ", ".join(llm_results["keywords"]) + "</p>")

        # 2. Create patient data and transfer request
        try:
            patient_location = Location(
                latitude=float(self.lat_input.text()),
                longitude=float(self.lon_input.text()),
            )
        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                "Invalid coordinates. Please select a valid location.",
            )
            return

        patient_data = PatientData(
            patient_id=self.patient_id_input.text(),
            chief_complaint=llm_results.get("chief_complaint", "Not specified"),
            clinical_history=llm_results.get("clinical_history", clinical_text),
            vital_signs=llm_results.get("vital_signs", {}),
            labs={},  # Not provided in this UI
            current_location=patient_location,
        )

        # Handle transport modes
        transport_modes = []
        transport_type = self.transport_combo.currentText()

        if transport_type == "POV (Private Vehicle)":
            transport_modes = [
                TransportMode.GROUND_AMBULANCE
            ]  # Use ground as proxy for POV
        elif transport_type == "Local EMS":
            transport_modes = [TransportMode.GROUND_AMBULANCE]
        else:  # Kangaroo Crew
            if self.kc_ground.isChecked():
                transport_modes = [TransportMode.GROUND_AMBULANCE]
            else:
                transport_modes = [TransportMode.AIR_AMBULANCE]

        transfer_request = TransferRequest(
            request_id=f"GUI_{
                patient_data.patient_id}_{
                datetime.now().strftime('%Y%m%d%H%M%S')}",
            patient_data=patient_data,
            sending_facility_name=self.sending_facility.text(),
            sending_facility_location=Location(
                latitude=float(self.lat_input.text()),
                longitude=float(self.lon_input.text()),
            ),
            preferred_transport_mode=transport_modes[0] if transport_modes else None,
        )

        # 3. Estimate transport times with traffic/ETA consideration
        if self.has_eta_checkbox.isChecked():
            eta_time = self.eta_time.time()
            current_time = QTime.currentTime()

            # Calculate minutes until ETA
            current_minutes = current_time.hour() * 60 + current_time.minute()
            eta_minutes = eta_time.hour() * 60 + eta_time.minute()

            # Handle crossing midnight
            if eta_minutes < current_minutes:
                eta_minutes += 24 * 60

            minutes_until_eta = eta_minutes - current_minutes
        else:
            minutes_until_eta = None

        # Calculate transport details
        transport_details = self.transport_estimator.estimate_transport_times(
            transfer_request.sending_facility_location,
            self.hospitals,
            transport_modes,
            minutes_until_eta=minutes_until_eta,
            transport_type=transport_type,
            kc_mode=(
                "fixed_wing"
                if self.kc_fixed.isChecked()
                else "helicopter" if self.kc_rotor.isChecked() else "ground"
            ),
        )

        # Display transport analysis
        self.transport_output.clear()
        self.transport_output.append("<h3>Transport Time Analysis</h3>")

        for hospital_id, details in transport_details.items():
            hospital_name = next(
                (h.name for h in self.hospitals if h.campus_id == hospital_id),
                hospital_id,
            )
            self.transport_output.append(f"<h4>{hospital_name}</h4>")
            self.transport_output.append(
                f"<p><b>Estimated Travel Time:</b> {details['time_minutes']} minutes</p>"
            )
            self.transport_output.append(
                f"<p><b>Distance:</b> {details['distance_km']:.1f} km</p>"
            )
            self.transport_output.append(
                f"<p><b>Transport Mode:</b> {details['mode']}</p>"
            )

            if "traffic_factor" in details:
                self.transport_output.append(
                    f"<p><b>Traffic Factor:</b> {details['traffic_factor']:.2f}x</p>"
                )

            if "notes" in details and details["notes"]:
                self.transport_output.append(f"<p><b>Notes:</b> {details['notes']}</p>")

            self.transport_output.append("<hr>")

        # 4. Call recommend_campus with all the data
        if not self.hospitals:
            QMessageBox.warning(
                self,
                "Configuration Error",
                "No hospital data loaded. Cannot generate recommendation.",
            )
            return

        if not self.weather_data:
            # Create default weather data if none loaded
            self.weather_data = WeatherData(
                temperature_celsius=25.0,
                wind_speed_kph=10.0,
                precipitation_mm_hr=0.0,
                visibility_km=10.0,
                adverse_conditions=[],
            )

        # Include human suggestions in the recommendation process
        human_suggestions = self._get_human_suggestions()

        # Call the recommendation engine
        try:
            recommendation = recommend_campus(
                request=transfer_request,
                campuses=self.hospitals,
                current_weather=self.weather_data,
                available_transport_modes=transport_modes,
                transport_time_estimates=transport_details,
                human_suggestions=human_suggestions,
            )

            # 5. Display results
            self._display_recommendation(recommendation)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Recommendation Error",
                f"Error generating recommendation: {str(e)}",
            )
            import traceback

            self.recommendation_output.setText(traceback.format_exc())

        # Save settings
        self._save_settings()

    def _get_human_suggestions(self) -> Dict:
        """Get human suggestions from the UI."""
        suggestions = {}

        # Care level suggestions
        care_levels = []
        if self.icu_checkbox.isChecked():
            care_levels.append("ICU")
        if self.picu_checkbox.isChecked():
            care_levels.append("PICU")
        if self.nicu_checkbox.isChecked():
            care_levels.append("NICU")

        if care_levels:
            suggestions["care_level"] = care_levels

        # Location preference
        location_pref = self.location_combo.currentText()
        if location_pref != "No preference":
            suggestions["location_preference"] = location_pref.replace("Prefers ", "")

        # Additional suggestions
        additional = self.additional_suggestions.toPlainText().strip()
        if additional:
            suggestions["additional_notes"] = additional

        return suggestions

    def _display_recommendation(self, recommendation: Optional[Recommendation]):
        """Display the recommendation results."""
        self.recommendation_output.clear()
        self.explanation_output.clear()

        if not recommendation:
            self.recommendation_output.append("<h3>No Recommendation Available</h3>")
            self.recommendation_output.append(
                "<p>The system could not determine a suitable recommendation based on the provided information.</p>"
            )
            return

        # Find the recommended hospital
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
        self.recommendation_output.append(f"<h2>Recommendation: {hospital_name}</h2>")
        self.recommendation_output.append(
            f"<p><b>Confidence:</b> {recommendation.confidence_score:.1f}%</p>"
        )
        self.recommendation_output.append(
            f"<p><b>Reason:</b> {recommendation.reason}</p>"
        )

        if recommended_hospital:
            self.recommendation_output.append("<h3>Hospital Details</h3>")
            self.recommendation_output.append(
                f"<p><b>Location:</b> {recommended_hospital.address}</p>"
            )
            self.recommendation_output.append("<p><b>Bed Availability:</b></p><ul>")
            self.recommendation_output.append(
                f"<li>General: {
                    recommended_hospital.bed_census.available_beds}/{
                    recommended_hospital.bed_census.total_beds}</li>"
            )
            self.recommendation_output.append(
                f"<li>ICU: {
                    recommended_hospital.bed_census.icu_beds_available}/{
                    recommended_hospital.bed_census.icu_beds_total}</li>"
            )
            self.recommendation_output.append(
                f"<li>NICU: {
                    recommended_hospital.bed_census.nicu_beds_available}/{
                    recommended_hospital.bed_census.nicu_beds_total}</li>"
            )
            self.recommendation_output.append("</ul>")

        # Display decision notes
        if recommendation.notes:
            self.recommendation_output.append("<h3>Decision Notes</h3><ul>")
            for note in recommendation.notes:
                self.recommendation_output.append(f"<li>{note}</li>")
            self.recommendation_output.append("</ul>")

        # Display explainability details in the explanation tab
        if recommendation.explainability_details:
            self.explanation_output.append("<h3>Recommendation Explanation</h3>")

            # Format the explainability details
            if isinstance(recommendation.explainability_details, dict):
                for category, details in recommendation.explainability_details.items():
                    self.explanation_output.append(
                        f"<h4>{category.replace('_', ' ').title()}</h4>"
                    )

                    if isinstance(details, dict):
                        self.explanation_output.append("<ul>")
                        for k, v in details.items():
                            self.explanation_output.append(f"<li><b>{k}:</b> {v}</li>")
                        self.explanation_output.append("</ul>")
                    elif isinstance(details, list):
                        self.explanation_output.append("<ul>")
                        for item in details:
                            self.explanation_output.append(f"<li>{item}</li>")
                        self.explanation_output.append("</ul>")
                    else:
                        self.explanation_output.append(f"<p>{details}</p>")
            else:
                self.explanation_output.append(
                    f"<p>{str(recommendation.explainability_details)}</p>"
                )


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

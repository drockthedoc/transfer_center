"""
Hospital Search Widget for the Transfer Center GUI.

This module contains the hospital search widget used in the main application window.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.hospital_search import HospitalSearch


class HospitalSearchWidget(QWidget):
    """Widget for searching and selecting hospitals."""

    hospital_selected = pyqtSignal(dict)  # Signal when a hospital is selected

    def __init__(self, parent=None):
        """Initialize the hospital search widget."""
        super().__init__(parent)
        self.hospital_search = HospitalSearch()
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Sending facility group
        sending_group = QGroupBox("Sending Facility")
        sending_layout = QVBoxLayout()
        sending_layout.setContentsMargins(5, 5, 5, 5)
        sending_layout.setSpacing(3)

        # Search interface
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter hospital name or address")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._search_hospital)
        search_layout.addWidget(self.search_input, 4)
        search_layout.addWidget(self.search_button, 1)
        sending_layout.addLayout(search_layout)

        # Results list
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(100)
        self.results_list.itemClicked.connect(self._select_hospital)
        sending_layout.addWidget(self.results_list)

        # Location display
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel("Latitude:"))
        self.latitude_input = QLineEdit()
        self.latitude_input.setReadOnly(True)
        coord_layout.addWidget(self.latitude_input)
        coord_layout.addWidget(QLabel("Longitude:"))
        self.longitude_input = QLineEdit()
        self.longitude_input.setReadOnly(True)
        coord_layout.addWidget(self.longitude_input)
        sending_layout.addLayout(coord_layout)

        sending_group.setLayout(sending_layout)
        layout.addWidget(sending_group)

    def _search_hospital(self):
        """Search for hospitals based on user input."""
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()
        results = self.hospital_search.search_hospitals(query)
        
        for result in results:
            item = QListWidgetItem(f"{result['name']} - {result['address']}")
            item.setData(256, result)  # Store the full result data
            self.results_list.addItem(item)

    def _select_hospital(self, item):
        """Handle hospital selection from search results."""
        result = item.data(256)
        if result:
            # Handle different possible formats for location data
            if "location" in result:
                # Nested location object format
                if isinstance(result["location"], dict):
                    if "lat" in result["location"] and "lng" in result["location"]:
                        # Format: {"location": {"lat": 123, "lng": 456}}
                        self.latitude_input.setText(str(result["location"]["lat"]))
                        self.longitude_input.setText(str(result["location"]["lng"]))
                    elif "latitude" in result["location"] and "longitude" in result["location"]:
                        # Format: {"location": {"latitude": 123, "longitude": 456}}
                        self.latitude_input.setText(str(result["location"]["latitude"]))
                        self.longitude_input.setText(str(result["location"]["longitude"]))
            elif "latitude" in result and "longitude" in result:
                # Direct coordinate format: {"latitude": 123, "longitude": 456}
                self.latitude_input.setText(str(result["latitude"]))
                self.longitude_input.setText(str(result["longitude"]))
                
            # Emit the selected hospital data
            self.hospital_selected.emit(result)

    def get_location_data(self):
        """Get the selected location data."""
        try:
            lat = float(self.latitude_input.text())
            lng = float(self.longitude_input.text())
            return {"latitude": lat, "longitude": lng}
        except (ValueError, TypeError):
            return None

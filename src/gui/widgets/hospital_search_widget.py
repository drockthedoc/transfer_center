from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout, QTextBrowser, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Optional, List, Dict, Any

# Actual model imports
from ...core.models import (
    HospitalCampus, Location, BedCensus, CampusExclusion, 
    HelipadData, CareLevel, Specialty, MetroArea
)

class HospitalSearchWidget(QWidget):
    # Signal to emit when a hospital is selected from the search results
    # Passes the full HospitalCampus object (or its ID/relevant data)
    hospital_selected = pyqtSignal(object) # Emits HospitalCampus object
    search_requested = pyqtSignal(str) # Emits search query string

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Sending Facility / Hospital Search")
        self._init_ui()
        self._current_search_results: List[HospitalCampus] = []

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Search Input --- 
        search_group = QGroupBox("Search for Hospital/Facility")
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter hospital name or address...")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search_clicked)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)

        # --- Search Results --- 
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        self.results_list_widget = QListWidget()
        self.results_list_widget.itemClicked.connect(self._on_result_selected)
        results_layout.addWidget(self.results_list_widget)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        # --- Selected Hospital Details --- 
        details_group = QGroupBox("Selected Facility Details")
        details_form_layout = QFormLayout()
        details_form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)

        self.name_label = QLabel("N/A")
        self.address_label = QLabel("N/A")
        self.latitude_label = QLabel("N/A")
        self.longitude_label = QLabel("N/A")
        self.phone_label = QLabel("N/A")
        self.website_label = QTextBrowser()
        self.website_label.setOpenExternalLinks(True)
        self.website_label.setReadOnly(True)
        self.website_label.setFrameStyle(QFrame.NoFrame)
        self.website_label.setFixedHeight(30)
        self.care_levels_display = QTextBrowser()
        self.care_levels_display.setReadOnly(True)
        self.care_levels_display.setFrameStyle(QFrame.NoFrame)
        self.care_levels_display.setFixedHeight(60)
        self.specialties_display = QTextBrowser()
        self.specialties_display.setReadOnly(True)
        self.specialties_display.setFrameStyle(QFrame.NoFrame)
        self.specialties_display.setFixedHeight(60)

        details_form_layout.addRow("Name:", self.name_label)
        details_form_layout.addRow("Address:", self.address_label)
        details_form_layout.addRow("Latitude:", self.latitude_label)
        details_form_layout.addRow("Longitude:", self.longitude_label)
        details_form_layout.addRow("Phone:", self.phone_label)
        details_form_layout.addRow("Website:", self.website_label)
        details_form_layout.addRow("Care Levels:", self.care_levels_display)
        details_form_layout.addRow("Specialties:", self.specialties_display)
        details_group.setLayout(details_form_layout)
        main_layout.addWidget(details_group)

        self.setLayout(main_layout)

    def _on_search_clicked(self):
        query = self.search_input.text().strip()
        if query:
            self.search_requested.emit(query)
        else:
            self.update_search_results([]) # Clear results if query is empty

    def _on_result_selected(self, item: QListWidgetItem):
        row = self.results_list_widget.row(item)
        if 0 <= row < len(self._current_search_results):
            selected_hospital = self._current_search_results[row]
            self.display_hospital_details(selected_hospital)
            self.hospital_selected.emit(selected_hospital)

    def update_search_results(self, hospitals: List[HospitalCampus]):
        self.results_list_widget.clear()
        self._current_search_results = hospitals
        if not hospitals:
            self.results_list_widget.addItem("No results found or search not performed.")
            self.clear_details()
            return

        for hospital in hospitals:
            name = getattr(hospital, 'name', 'Unknown Hospital')
            address = getattr(hospital, 'address', 'No address')
            list_item_text = f"{name} - {address}"
            self.results_list_widget.addItem(QListWidgetItem(list_item_text))
        
        # Optionally, select the first item by default
        if hospitals:
            self.results_list_widget.setCurrentRow(0)
            self.display_hospital_details(hospitals[0])
            # self.hospital_selected.emit(hospitals[0]) # Decide if selection should auto-emit
        else:
            self.clear_details()

    def display_hospital_details(self, hospital: Optional[HospitalCampus]):
        if not hospital:
            self.clear_details()
            return

        self.name_label.setText(getattr(hospital, 'name', 'N/A'))
        self.address_label.setText(getattr(hospital, 'address', 'N/A'))
        
        loc = getattr(hospital, 'location', None)
        self.latitude_label.setText(str(getattr(loc, 'latitude', 'N/A')) if loc else 'N/A')
        self.longitude_label.setText(str(getattr(loc, 'longitude', 'N/A')) if loc else 'N/A')
        
        self.phone_label.setText(getattr(hospital, 'phone', 'N/A') or 'N/A')
        website_url = getattr(hospital, 'website', None)
        if website_url:
            self.website_label.setHtml(f'<a href="{website_url}">{website_url}</a>')
        else:
            self.website_label.setHtml("N/A")

        care_levels_list = [str(cl.value if hasattr(cl, 'value') else cl) for cl in getattr(hospital, 'care_levels', [])]
        self.care_levels_display.setHtml(", ".join(care_levels_list) or "N/A")

        specialties_list = [str(sp.value if hasattr(sp, 'value') else sp) for sp in getattr(hospital, 'specialties', [])]
        self.specialties_display.setHtml(", ".join(specialties_list) or "N/A")

    def get_selected_hospital_location(self) -> Optional[Dict[str, float]]:
        # This method is to provide the location for the main window if needed
        # based on the currently displayed details.
        try:
            lat_str = self.latitude_label.text()
            lon_str = self.longitude_label.text()
            if lat_str != 'N/A' and lon_str != 'N/A':
                return {"latitude": float(lat_str), "longitude": float(lon_str)}
        except ValueError:
            return None
        return None

    def clear_details(self):
        self.name_label.setText("N/A")
        self.address_label.setText("N/A")
        self.latitude_label.setText("N/A")
        self.longitude_label.setText("N/A")
        self.phone_label.setText("N/A")
        self.website_label.setHtml("N/A")
        self.care_levels_display.setHtml("N/A")
        self.specialties_display.setHtml("N/A")

    def clear_all(self):
        self.search_input.clear()
        self.results_list_widget.clear()
        self._current_search_results = []
        self.clear_details()

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    # Dummy classes for testing
    class DummyLocation:
        def __init__(self, latitude, longitude):
            self.latitude = latitude
            self.longitude = longitude

    class DummyHospitalCampus:
        def __init__(self, campus_id, name, address, lat, lon, phone=None, website=None, care_levels=None, specialties=None):
            self.campus_id = campus_id
            self.name = name
            self.address = address
            self.location = DummyLocation(lat, lon)
            self.phone = phone
            self.website = website
            self.care_levels = care_levels or []
            self.specialties = specialties or []
            # Add other fields like bed_census, exclusions if needed for full testing
            self.bed_census = None 
            self.exclusions = []
            self.helipads = []
            self.is_pediatric_hospital = False
            self.metro_area = None

    app = QApplication(sys.argv)
    # Monkey patch for testing
    HospitalSearchWidget.HospitalCampus = DummyHospitalCampus
    HospitalSearchWidget.Location = DummyLocation
    # ... add other dummy models if their attributes are directly accessed

    widget = HospitalSearchWidget()

    # Example usage: Simulate receiving search results
    results_data = [
        DummyHospitalCampus("HC001", "General Hospital Downtown", "123 Main St, Cityville", 34.0522, -118.2437, "555-1234", "http://generalhospital.org", ["General", "ICU"], ["Cardiology", "Neurology"]),
        DummyHospitalCampus("HC002", "Suburb Community Hospital", "456 Oak Ave, Suburbia", 34.0000, -118.1000, "555-5678", "http://suburbcomhospital.com", ["General"], ["Pediatrics"])
    ]
    # widget.update_search_results(results_data)

    def handle_search_request(query):
        print(f"Search requested for: {query}")
        # In a real app, this would trigger a backend search
        # For testing, we'll just populate with dummy data if query is 'test'
        if query.lower() == 'test':
            widget.update_search_results(results_data)
        else:
            widget.update_search_results([])
    
    def handle_hospital_selection(hospital):
        print(f"Hospital selected: {hospital.name} (ID: {hospital.campus_id})")
        selected_loc = widget.get_selected_hospital_location()
        if selected_loc:
            print(f"Selected Location from widget: Lat {selected_loc['latitude']}, Lon {selected_loc['longitude']}")

    widget.search_requested.connect(handle_search_request)
    widget.hospital_selected.connect(handle_hospital_selection)
    
    widget.show()
    widget.search_input.setText("test") # Simulate user typing 'test'
    widget.search_button.click() # Simulate clicking search

    sys.exit(app.exec_())

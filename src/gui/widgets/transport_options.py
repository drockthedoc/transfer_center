from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QGroupBox, QTextBrowser, QFrame
)
from PyQt5.QtCore import Qt
from typing import Optional, Dict, Any

# Actual model import
from ...core.models import Recommendation # Assuming Recommendation holds all necessary transport fields

class TransportOptionsWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Transport Information")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        transport_group = QGroupBox("Selected Transport & Conditions")
        form_layout = QFormLayout(transport_group)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)

        self.chosen_mode_label = QLabel("N/A")
        self.travel_time_label = QLabel("N/A")
        
        self.details_browser = QTextBrowser()
        self.details_browser.setReadOnly(True)
        self.details_browser.setOpenExternalLinks(False) # No external links expected here
        self.details_browser.setFrameStyle(QFrame.NoFrame)
        self.details_browser.setFixedHeight(100)

        self.weather_browser = QTextBrowser()
        self.weather_browser.setReadOnly(True)
        self.weather_browser.setFrameStyle(QFrame.NoFrame)
        self.weather_browser.setFixedHeight(80)

        self.traffic_browser = QTextBrowser()
        self.traffic_browser.setReadOnly(True)
        self.traffic_browser.setFrameStyle(QFrame.NoFrame)
        self.traffic_browser.setFixedHeight(80)

        form_layout.addRow("<b>Chosen Transport Mode:</b>", self.chosen_mode_label)
        form_layout.addRow("<b>Estimated Travel Time:</b>", self.travel_time_label)
        form_layout.addRow(QLabel("<b>Other Transport Details:</b>"))
        form_layout.addRow(self.details_browser)
        form_layout.addRow(QLabel("<b>Weather Conditions:</b>"))
        form_layout.addRow(self.weather_browser)
        form_layout.addRow(QLabel("<b>Traffic Conditions:</b>"))
        form_layout.addRow(self.traffic_browser)
        
        transport_group.setLayout(form_layout)
        main_layout.addWidget(transport_group)
        self.setLayout(main_layout)

    def _format_dict_to_html_list(self, data: Dict[str, Any]) -> str:
        if not data:
            return "<p>N/A</p>"
        html = "<ul>"
        for key, value in data.items():
            html += f"<li><b>{key.replace('_', ' ').title()}:</b> {value}</li>"
        html += "</ul>"
        return html

    def update_transport_info(self, recommendation: Optional[Recommendation]):
        if not recommendation:
            self.clear_display()
            return

        self.chosen_mode_label.setText(getattr(recommendation, 'chosen_transport_mode', 'N/A') or 'N/A')
        
        travel_time_min = getattr(recommendation, 'final_travel_time_minutes', None)
        if travel_time_min is not None:
            self.travel_time_label.setText(f"{travel_time_min:.0f} minutes")
        else:
            # Fallback to transport_details if final_travel_time_minutes is not set
            transport_dict = getattr(recommendation, 'transport_details', {})
            est_time = transport_dict.get('estimated_time_minutes')
            self.travel_time_label.setText(f"{est_time:.0f} minutes (est.)" if est_time is not None else "N/A")

        transport_details_dict = getattr(recommendation, 'transport_details', {})
        self.details_browser.setHtml(self._format_dict_to_html_list(transport_details_dict))
        
        conditions_dict = getattr(recommendation, 'conditions', {})
        weather_dict = conditions_dict.get('weather', {})
        self.weather_browser.setHtml(self._format_dict_to_html_list(weather_dict))
        
        traffic_dict = conditions_dict.get('traffic', {})
        self.traffic_browser.setHtml(self._format_dict_to_html_list(traffic_dict))

    def clear_display(self):
        self.chosen_mode_label.setText("N/A")
        self.travel_time_label.setText("N/A")
        self.details_browser.setHtml("<p>N/A</p>")
        self.weather_browser.setHtml("<p>N/A</p>")
        self.traffic_browser.setHtml("<p>N/A</p>")

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    # Dummy Recommendation for testing
    class DummyRecommendation:
        def __init__(self):
            self.chosen_transport_mode = "Ground Ambulance"
            self.final_travel_time_minutes = 45.0
            self.transport_details = {
                "vehicle_id": "ALS Unit 7",
                "crew_type": "Paramedic, EMT",
                "estimated_cost_usd": 350,
                "special_notes": "Patient requires cardiac monitoring during transport."
            }
            self.conditions = {
                "weather": {"summary": "Partly Cloudy", "temperature_c": 18, "wind_mph": 12, "precipitation_chance": "10%"},
                "traffic": {"level": "Moderate", "description": "Minor congestion on I-10 Eastbound"}
            }

    app = QApplication(sys.argv)
    TransportOptionsWidget.Recommendation = DummyRecommendation # Monkey patch
    
    widget = TransportOptionsWidget()
    
    # Test with data
    rec = DummyRecommendation()
    widget.update_transport_info(rec)
    widget.show()
    widget.resize(400, 350)

    # Test clearing
    # widget.clear_display()
    # widget.show()

    sys.exit(app.exec_())

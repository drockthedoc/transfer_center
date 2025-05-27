from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QTextBrowser, QScrollArea, QGroupBox, QFormLayout, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt
from typing import Optional, Dict, Any, List, Union

# Assuming Recommendation and LLMReasoningDetails are imported from src.core.models
# This is a placeholder; actual import path might differ based on project structure.
# from ....core.models import Recommendation, LLMReasoningDetails, ScoringResult
# For now, let's define dummy classes if direct import is problematic in this context
# In a real scenario, ensure these are correctly imported.
class Recommendation:
    pass
class LLMReasoningDetails:
    pass
class ScoringResult:
    pass    

class RecommendationOutputWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Recommendation Details")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create tabs
        self.main_rec_tab = QWidget()
        self.explainability_tab = QWidget()
        self.transport_tab = QWidget()
        self.scoring_notes_tab = QWidget()

        self.tabs.addTab(self.main_rec_tab, "Main Recommendation")
        self.tabs.addTab(self.explainability_tab, "Explainability")
        self.tabs.addTab(self.transport_tab, "Transport & Conditions")
        self.tabs.addTab(self.scoring_notes_tab, "Scoring & Notes")

        # Setup UI for each tab
        self._setup_main_rec_tab()
        self._setup_explainability_tab()
        self._setup_transport_tab()
        self._setup_scoring_notes_tab()

        self.setLayout(main_layout)
        self.setMinimumHeight(400)
        self.setMinimumWidth(600)

    def _create_label_value_display(self, label_text: str, is_html: bool = False) -> (QLabel, Union[QLabel, QTextBrowser]):
        label = QLabel(f"<b>{label_text}:</b>")
        if is_html:
            value_display = QTextBrowser()
            value_display.setReadOnly(True)
            value_display.setOpenExternalLinks(True)
            value_display.setFrameStyle(QFrame.NoFrame)
            value_display.setFixedHeight(100) # Default height, can be adjusted
        else:
            value_display = QLabel("N/A")
            value_display.setWordWrap(True)
        return label, value_display

    def _setup_main_rec_tab(self):
        layout = QFormLayout(self.main_rec_tab)
        layout.setRowWrapPolicy(QFormLayout.WrapAllRows)

        _, self.campus_name_label = self._create_label_value_display("Recommended Campus")
        _, self.care_level_label = self._create_label_value_display("Recommended Care Level")
        _, self.confidence_label = self._create_label_value_display("Confidence Score")
        _, self.brief_reason_html = self._create_label_value_display("Brief Reason", is_html=True)
        self.brief_reason_html.setFixedHeight(150)

        layout.addRow("Recommended Campus:", self.campus_name_label)
        layout.addRow("Recommended Care Level:", self.care_level_label)
        layout.addRow("Confidence Score:", self.confidence_label)
        layout.addRow("Brief Reason:", self.brief_reason_html)
        self.main_rec_tab.setLayout(layout)

    def _setup_explainability_tab(self):
        layout = QVBoxLayout(self.explainability_tab)
        
        main_reason_group = QGroupBox("Main LLM Recommendation Reason")
        main_reason_layout = QVBoxLayout()
        self.main_llm_reason_html = QTextBrowser()
        self.main_llm_reason_html.setReadOnly(True)
        self.main_llm_reason_html.setOpenExternalLinks(True)
        main_reason_layout.addWidget(self.main_llm_reason_html)
        main_reason_group.setLayout(main_reason_layout)
        layout.addWidget(main_reason_group)

        key_factors_group = QGroupBox("Key Factors Considered by LLM")
        key_factors_layout = QVBoxLayout()
        self.key_factors_html = QTextBrowser()
        self.key_factors_html.setReadOnly(True)
        key_factors_layout.addWidget(self.key_factors_html)
        key_factors_group.setLayout(key_factors_layout)
        layout.addWidget(key_factors_group)

        alt_reasons_group = QGroupBox("Alternative Hospital Considerations")
        alt_reasons_layout = QVBoxLayout()
        self.alt_reasons_html = QTextBrowser()
        self.alt_reasons_html.setReadOnly(True)
        self.alt_reasons_html.setOpenExternalLinks(True)
        alt_reasons_layout.addWidget(self.alt_reasons_html)
        alt_reasons_group.setLayout(alt_reasons_layout)
        layout.addWidget(alt_reasons_group)
        
        confidence_exp_group = QGroupBox("Confidence Explanation")
        confidence_exp_layout = QVBoxLayout()
        self.confidence_exp_html = QTextBrowser()
        self.confidence_exp_html.setReadOnly(True)
        confidence_exp_layout.addWidget(self.confidence_exp_html)
        confidence_exp_group.setLayout(confidence_exp_layout)
        layout.addWidget(confidence_exp_group)

        simple_exp_group = QGroupBox("Simple Rule-Based Explanation")
        simple_exp_layout = QVBoxLayout()
        self.simple_explanation_html = QTextBrowser()
        self.simple_explanation_html.setReadOnly(True)
        simple_exp_layout.addWidget(self.simple_explanation_html)
        simple_exp_group.setLayout(simple_exp_layout)
        layout.addWidget(simple_exp_group)
        
        self.explainability_tab.setLayout(layout)

    def _setup_transport_tab(self):
        layout = QFormLayout(self.transport_tab)
        layout.setRowWrapPolicy(QFormLayout.WrapAllRows)

        _, self.transport_mode_label = self._create_label_value_display("Chosen Transport Mode")
        _, self.travel_time_label = self._create_label_value_display("Estimated Travel Time")
        _, self.transport_details_html = self._create_label_value_display("Other Transport Details", is_html=True)
        self.transport_details_html.setFixedHeight(150)
        _, self.weather_conditions_html = self._create_label_value_display("Weather Conditions", is_html=True)
        self.weather_conditions_html.setFixedHeight(100)
        _, self.traffic_conditions_html = self._create_label_value_display("Traffic Conditions", is_html=True)
        self.traffic_conditions_html.setFixedHeight(100)

        layout.addRow("Chosen Transport Mode:", self.transport_mode_label)
        layout.addRow("Estimated Travel Time:", self.travel_time_label)
        layout.addRow("Other Transport Details:", self.transport_details_html)
        layout.addRow("Weather Conditions:", self.weather_conditions_html)
        layout.addRow("Traffic Conditions:", self.traffic_conditions_html)
        self.transport_tab.setLayout(layout)

    def _setup_scoring_notes_tab(self):
        layout = QVBoxLayout(self.scoring_notes_tab)

        scoring_group = QGroupBox("Scoring Results Summary")
        scoring_layout = QVBoxLayout()
        self.scoring_results_html = QTextBrowser()
        self.scoring_results_html.setReadOnly(True)
        scoring_layout.addWidget(self.scoring_results_html)
        scoring_group.setLayout(scoring_layout)
        layout.addWidget(scoring_group)

        notes_group = QGroupBox("Process Notes")
        notes_layout = QVBoxLayout()
        self.notes_html = QTextBrowser()
        self.notes_html.setReadOnly(True)
        notes_layout.addWidget(self.notes_html)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        self.scoring_notes_tab.setLayout(layout)

    def _format_dict_to_html(self, data: Dict[str, Any], title: Optional[str] = None) -> str:
        if not data:
            return "<p>N/A</p>"
        html = f"<h3>{title}</h3>" if title else ""
        html += "<ul>"
        for key, value in data.items():
            html += f"<li><b>{key.replace('_', ' ').title()}:</b> {value}</li>"
        html += "</ul>"
        return html

    def _format_list_to_html(self, data: List[str], title: Optional[str] = None) -> str:
        if not data:
            return "<p>N/A</p>"
        html = f"<h3>{title}</h3>" if title else ""
        html += "<ul>"
        for item in data:
            html += f"<li>{item}</li>"
        html += "</ul>"
        return html

    def set_recommendation(self, recommendation: Optional[Recommendation], error_message: Optional[str] = None):
        if error_message:
            self.tabs.setCurrentIndex(0) # Show main tab for error
            self.campus_name_label.setText(f"<font color='red'>ERROR</font>")
            self.care_level_label.setText("N/A")
            self.confidence_label.setText("N/A")
            self.brief_reason_html.setHtml(f"<font color='red'>{error_message}</font>")
            # Clear other fields or set to error status
            self.main_llm_reason_html.setHtml("<p>Error occurred.</p>")
            self.key_factors_html.setHtml("<p>Error occurred.</p>")
            self.alt_reasons_html.setHtml("<p>Error occurred.</p>")
            self.confidence_exp_html.setHtml("<p>Error occurred.</p>")
            self.simple_explanation_html.setHtml("<p>Error occurred.</p>")
            self.transport_mode_label.setText("N/A")
            self.travel_time_label.setText("N/A")
            self.transport_details_html.setHtml("<p>Error occurred.</p>")
            self.weather_conditions_html.setHtml("<p>Error occurred.</p>")
            self.traffic_conditions_html.setHtml("<p>Error occurred.</p>")
            self.scoring_results_html.setHtml("<p>Error occurred.</p>")
            self.notes_html.setHtml(f"<p><b>Error Details:</b> {error_message}</p>")
            return

        if not recommendation:
            self.set_recommendation(None, "No recommendation data available.") # Recurse with error
            return

        # Main Recommendation Tab
        self.campus_name_label.setText(getattr(recommendation, 'recommended_campus_name', 'N/A') or 'N/A')
        self.care_level_label.setText(getattr(recommendation, 'recommended_level_of_care', 'N/A') or 'General')
        confidence = getattr(recommendation, 'confidence_score', 0.0)
        self.confidence_label.setText(f"{confidence:.1f}%" if confidence is not None else "N/A")
        self.brief_reason_html.setHtml(getattr(recommendation, 'reason', 'N/A') or 'N/A')

        # Explainability Tab
        explain_details = getattr(recommendation, 'explainability_details', None)
        if explain_details:
            self.main_llm_reason_html.setHtml(getattr(explain_details, 'main_recommendation_reason', 'N/A') or 'N/A')
            self.key_factors_html.setHtml(self._format_list_to_html(getattr(explain_details, 'key_factors_considered', []))) 
            self.alt_reasons_html.setHtml(self._format_dict_to_html(getattr(explain_details, 'alternative_reasons', {}), title="Alternative Hospital Considerations"))
            self.confidence_exp_html.setHtml(getattr(explain_details, 'confidence_explanation', 'N/A') or 'N/A')
        else:
            self.main_llm_reason_html.setHtml("N/A")
            self.key_factors_html.setHtml("N/A")
            self.alt_reasons_html.setHtml("N/A")
            self.confidence_exp_html.setHtml("N/A")
            
        simple_exp = getattr(recommendation, 'simple_explanation', {})
        self.simple_explanation_html.setHtml(self._format_dict_to_html(simple_exp, title="Rule-Based Explanation Factors"))

        # Transport & Conditions Tab
        self.transport_mode_label.setText(getattr(recommendation, 'chosen_transport_mode', 'N/A') or 'N/A')
        travel_time_min = getattr(recommendation, 'final_travel_time_minutes', None)
        if travel_time_min is not None:
            self.travel_time_label.setText(f"{travel_time_min:.0f} minutes")
        else:
            # Fallback to transport_details if final_travel_time_minutes is not set
            transport_dict = getattr(recommendation, 'transport_details', {})
            est_time = transport_dict.get('estimated_time_minutes')
            self.travel_time_label.setText(f"{est_time:.0f} minutes (est.)" if est_time is not None else "N/A")

        self.transport_details_html.setHtml(self._format_dict_to_html(getattr(recommendation, 'transport_details', {}), title="Transport Details"))
        
        conditions_dict = getattr(recommendation, 'conditions', {})
        self.weather_conditions_html.setHtml(self._format_dict_to_html(conditions_dict.get('weather', {}), title="Weather"))
        self.traffic_conditions_html.setHtml(self._format_dict_to_html(conditions_dict.get('traffic', {}), title="Traffic"))

        # Scoring & Notes Tab
        scoring_data = getattr(recommendation, 'scoring_results', [])
        scoring_html = ""
        if scoring_data:
            scoring_html += "<ul>"
            for score_item in scoring_data: # Assuming ScoringResult has 'name' and 'score' attributes
                score_name = getattr(score_item, 'name', 'Unknown Score')
                score_value = getattr(score_item, 'score', 'N/A')
                score_rationale = getattr(score_item, 'rationale', '')
                scoring_html += f"<li><b>{score_name}:</b> {score_value} ({score_rationale})</li>"
            scoring_html += "</ul>"
        else:
            scoring_html = "<p>No scoring results available.</p>"
        self.scoring_results_html.setHtml(scoring_html)
        
        notes_data = getattr(recommendation, 'notes', [])
        self.notes_html.setHtml(self._format_list_to_html(notes_data, title="Process Notes"))

    def clear_display(self):
        """Clears all fields in the display."""
        self.set_recommendation(None, "Display cleared.") # Use error path to clear
        self.brief_reason_html.setHtml("") # Ensure main error message is also cleared


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    # Dummy data for testing
    class DummyLLMReasoningDetails:
        def __init__(self, main_recommendation_reason, key_factors_considered=None, alternative_reasons=None, confidence_explanation=None):
            self.main_recommendation_reason = main_recommendation_reason
            self.key_factors_considered = key_factors_considered or ["Distance: 25km", "Specialty: Cardiology Available"]
            self.alternative_reasons = alternative_reasons or {"Hospital B": "Longer ETA", "Hospital C": "No PICU"}
            self.confidence_explanation = confidence_explanation or "Confidence based on strong match for specialty and proximity."

    class DummyScoringResult:
        def __init__(self, name, score, rationale):
            self.name = name
            self.score = score
            self.rationale = rationale
            
    class DummyRecommendation:
        def __init__(self):
            self.transfer_request_id = "TR123"
            self.recommended_campus_id = "HC001"
            self.recommended_campus_name = "City General Hospital"
            self.reason = "Best match for required cardiac care and proximity. PICU available."
            self.confidence_score = 92.5
            self.recommended_level_of_care = "PICU"
            self.chosen_transport_mode = "Ground Ambulance"
            self.final_travel_time_minutes = 35.0
            self.transport_details = {
                "estimated_time_minutes": 35,
                "mode_details": "ALS Unit 12",
                "vehicle_availability": "Available",
                "special_equipment_needed": ["Ventilator", "IV Pump"]
            }
            self.conditions = {
                "weather": {"summary": "Clear", "temperature_c": 22, "wind_kph": 10},
                "traffic": {"level": "Light", "description": "No significant delays reported"}
            }
            self.explainability_details = DummyLLMReasoningDetails(
                main_recommendation_reason="The patient requires PICU level care and specialized cardiac consultation. City General Hospital has an available PICU bed, the required cardiac specialists on call, and is the closest facility meeting these critical needs. ETA via ground ambulance is approximately 35 minutes.",
            )
            self.notes = [
                "Initial request received.", 
                "Patient data parsed.", 
                "LLM processing initiated.", 
                "Distance calculation: City General (35min), St. Lukes (50min)",
                "Rule-based check: City General meets all criteria.",
                "Recommendation finalized."
            ]
            self.simple_explanation = {
                "Primary Need": "PICU Cardiac Care",
                "Hospital Match": "City General - PICU Available, Cardiac Specialty",
                "Proximity Factor": "Closest suitable facility (35 mins)"
            }
            self.scoring_results = [
                DummyScoringResult("Proximity Score", 90, "Within 30 miles"),
                DummyScoringResult("Specialty Match Score", 95, "Required specialties available"),
                DummyScoringResult("Bed Availability Score", 85, "PICU bed confirmed")
            ]

    app = QApplication(sys.argv)
    # Replace dummy classes with actual imports from src.core.models
    # This is just for standalone testing of the widget's appearance.
    RecommendationOutputWidget.Recommendation = DummyRecommendation
    RecommendationOutputWidget.LLMReasoningDetails = DummyLLMReasoningDetails
    RecommendationOutputWidget.ScoringResult = DummyScoringResult
    
    widget = RecommendationOutputWidget()
    
    # Test with data
    rec_data = DummyRecommendation()
    widget.set_recommendation(rec_data)
    widget.show()
    
    # Test with error
    # widget.set_recommendation(None, "This is a test error message.")
    # widget.show()

    # Test clearing
    # widget.clear_display()
    # widget.show()

    sys.exit(app.exec_())

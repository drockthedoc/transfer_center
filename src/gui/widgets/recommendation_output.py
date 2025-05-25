"""
Recommendation Output Widget for the Transfer Center GUI.

This module contains the recommendation output widget used in the main application window.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QGroupBox, QHBoxLayout, QLabel, QScrollArea, QTabWidget, 
                             QTextEdit, QVBoxLayout, QWidget)


class RecommendationOutputWidget(QWidget):
    """Widget for displaying recommendation output."""

    def __init__(self, parent=None):
        """Initialize the recommendation output widget."""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Create tabs for different output views
        self.output_tabs = QTabWidget()
        self.output_tabs.setDocumentMode(True)  # Make tabs more compact

        # Enhanced Recommendation tab
        self.recommendation_tab = QWidget()
        recommendation_layout = QVBoxLayout(self.recommendation_tab)
        recommendation_layout.setContentsMargins(5, 5, 5, 5)

        # Use a scrollable area for the recommendation to handle longer content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_area.setWidget(scroll_content)
        
        # Create header for the recommendation
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.recommendation_header = QLabel("TRANSFER RECOMMENDATION")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        self.recommendation_header.setFont(font)
        self.recommendation_header.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.recommendation_header)
        scroll_layout.addLayout(header_layout)
        
        # Sections for organized information display
        # Main recommendation section
        self.main_recommendation = QTextEdit()
        self.main_recommendation.setReadOnly(True)
        self.main_recommendation.setMinimumHeight(180)
        self.main_recommendation.setStyleSheet(
            "background-color: #e6f7ff; border: 1px solid #99d6ff; border-radius: 5px; color: #000000; font-size: 11pt;"
        )
        self.main_recommendation.setPlaceholderText("Primary recommendation will appear here...")
        scroll_layout.addWidget(self.main_recommendation)
        
        # Transport and logistics section
        transport_group = QGroupBox("Transport & Logistics")
        transport_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        transport_layout = QVBoxLayout(transport_group)
        
        self.transport_info = QTextEdit()
        self.transport_info.setReadOnly(True)
        self.transport_info.setMinimumHeight(150)
        self.transport_info.setStyleSheet(
            "background-color: #fff8e6; border: 1px solid #ffdb99; border-radius: 5px; color: #000000; font-size: 11pt;"
        )
        transport_layout.addWidget(self.transport_info)
        scroll_layout.addWidget(transport_group)
        
        # Weather and traffic section
        conditions_group = QGroupBox("Weather & Traffic Conditions")
        conditions_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        conditions_layout = QVBoxLayout(conditions_group)
        
        self.conditions_info = QTextEdit()
        self.conditions_info.setReadOnly(True)
        self.conditions_info.setMinimumHeight(150)
        self.conditions_info.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #d0d0d0; border-radius: 5px; color: #000000; font-size: 11pt;"
        )
        conditions_layout.addWidget(self.conditions_info)
        scroll_layout.addWidget(conditions_group)
        
        # Exclusions section
        exclusions_group = QGroupBox("Exclusion Criteria")
        exclusions_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        exclusions_layout = QVBoxLayout(exclusions_group)
        
        self.exclusions_info = QTextEdit()
        self.exclusions_info.setReadOnly(True)
        self.exclusions_info.setMinimumHeight(150)
        self.exclusions_info.setStyleSheet(
            "background-color: #ffebe6; border: 1px solid #ffb399; border-radius: 5px; color: #000000; font-size: 11pt;"
        )
        exclusions_layout.addWidget(self.exclusions_info)
        scroll_layout.addWidget(exclusions_group)
        
        # Alternative options section
        alternatives_group = QGroupBox("Alternative Options")
        alternatives_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        alternatives_layout = QVBoxLayout(alternatives_group)
        
        self.alternatives_info = QTextEdit()
        self.alternatives_info.setReadOnly(True)
        self.alternatives_info.setMinimumHeight(150)
        self.alternatives_info.setStyleSheet(
            "background-color: #e6ffe6; border: 1px solid #99ff99; border-radius: 5px; color: #000000; font-size: 11pt;"
        )
        alternatives_layout.addWidget(self.alternatives_info)
        scroll_layout.addWidget(alternatives_group)

        # LLM Reasoning Details Section
        self.llm_reasoning_group = QGroupBox("LLM Reasoning & Explainability")
        self.llm_reasoning_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        llm_reasoning_layout = QVBoxLayout(self.llm_reasoning_group)
        llm_reasoning_layout.setSpacing(8)

        self.lbl_primary_reason_title = QLabel("<b>Primary Reason:</b>")
        self.lbl_primary_reason_title.setTextFormat(Qt.RichText)
        llm_reasoning_layout.addWidget(self.lbl_primary_reason_title)
        self.lbl_primary_reason = QLabel("N/A")
        self.lbl_primary_reason.setWordWrap(True)
        self.lbl_primary_reason.setStyleSheet("font-size: 11pt; margin-left: 10px;")
        llm_reasoning_layout.addWidget(self.lbl_primary_reason)

        self.lbl_key_factors_title = QLabel("<b>Key Factors Considered:</b>")
        self.lbl_key_factors_title.setTextFormat(Qt.RichText)
        llm_reasoning_layout.addWidget(self.lbl_key_factors_title)
        self.factors_layout = QVBoxLayout() # To hold list of factors
        self.factors_layout.setContentsMargins(20, 0, 0, 0) # Indent factors
        llm_reasoning_layout.addLayout(self.factors_layout)
        self.lbl_no_factors = QLabel("- N/A") # Displayed if no factors
        self.lbl_no_factors.setStyleSheet("font-size: 11pt; margin-left: 10px;")
        self.factors_layout.addWidget(self.lbl_no_factors)


        self.lbl_alternative_reasons_title = QLabel("<b>Other Considerations:</b>")
        self.lbl_alternative_reasons_title.setTextFormat(Qt.RichText)
        llm_reasoning_layout.addWidget(self.lbl_alternative_reasons_title)
        self.alternatives_layout_group = QVBoxLayout() # To hold alternative reasons
        self.alternatives_layout_group.setContentsMargins(20,0,0,0)
        llm_reasoning_layout.addLayout(self.alternatives_layout_group)
        self.lbl_no_alternatives = QLabel("- N/A") # Displayed if no alternatives
        self.lbl_no_alternatives.setStyleSheet("font-size: 11pt; margin-left: 10px;")
        self.alternatives_layout_group.addWidget(self.lbl_no_alternatives)


        self.lbl_confidence_explanation_title = QLabel("<b>Confidence Note:</b>")
        self.lbl_confidence_explanation_title.setTextFormat(Qt.RichText)
        llm_reasoning_layout.addWidget(self.lbl_confidence_explanation_title)
        self.lbl_confidence_explanation = QLabel("N/A")
        self.lbl_confidence_explanation.setWordWrap(True)
        self.lbl_confidence_explanation.setStyleSheet("font-size: 11pt; margin-left: 10px;")
        llm_reasoning_layout.addWidget(self.lbl_confidence_explanation)
        
        scroll_layout.addWidget(self.llm_reasoning_group)
        
        # Add the complete recommendation area to the tab
        recommendation_layout.addWidget(scroll_area)
        self.output_tabs.addTab(self.recommendation_tab, "Recommendation")

        # Explanation tab (can be removed or repurposed if LLM reasoning is now in main tab)
        # For now, let's keep it but it might become redundant
        self.explanation_tab = QWidget()
        explanation_layout = QVBoxLayout(self.explanation_tab)
        explanation_layout.setContentsMargins(5, 5, 5, 5)

        self.explanation_output = QTextEdit()
        self.explanation_output.setReadOnly(True)
        self.explanation_output.setPlaceholderText(
            "Detailed explanation (legacy or additional) will appear here..."
        )
        explanation_layout.addWidget(self.explanation_output)

        self.output_tabs.addTab(self.explanation_tab, "Explanation (Legacy)")

        # Raw Data tab
        self.raw_tab = QWidget()
        raw_layout = QVBoxLayout(self.raw_tab)
        raw_layout.setContentsMargins(5, 5, 5, 5)

        self.raw_output = QTextEdit()
        self.raw_output.setReadOnly(True)
        self.raw_output.setPlaceholderText("Raw data will appear here...")
        raw_layout.addWidget(self.raw_output)

        self.output_tabs.addTab(self.raw_tab, "Raw Data")

        # Add the tabs to the layout
        layout.addWidget(self.output_tabs)

    def clear(self):
        """Clear all output fields."""
        self.main_recommendation.clear()
        self.transport_info.clear()
        self.conditions_info.clear()
        self.exclusions_info.clear()
        self.alternatives_info.clear()
        self.explanation_output.clear() # Keep for now, might be removed later
        self.raw_output.clear()
        
        # Clear LLM Reasoning section
        self.lbl_primary_reason.setText("N/A")
        self.lbl_confidence_explanation.setText("N/A")
        
        # Clear factors layout
        while self.factors_layout.count():
            child = self.factors_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.factors_layout.addWidget(self.lbl_no_factors) # Re-add N/A label
        self.lbl_no_factors.show()

        # Clear alternatives layout
        while self.alternatives_layout_group.count():
            child = self.alternatives_layout_group.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.alternatives_layout_group.addWidget(self.lbl_no_alternatives) # Re-add N/A label
        self.lbl_no_alternatives.show()


    def set_recommendation(self, recommendation_data):
        """Set the recommendation content with enhanced formatting.
        
        Args:
            recommendation_data: Dictionary containing recommendation sections.
                                 Expected to be a Recommendation Pydantic model's dict() output.
        """
        if not isinstance(recommendation_data, dict):
            error_msg = f"Unexpected recommendation data type: {type(recommendation_data).__name__}"
            if isinstance(recommendation_data, str):
                error_msg = recommendation_data
            elif recommendation_data is None:
                error_msg = "No recommendation data provided"
            
            self.recommendation_header.setStyleSheet("color: #cc0000;")
            self.main_recommendation.setHtml(
                f"<p><b>Error Generating Recommendation</b></p><p>{error_msg}</p>"
            )
            self.clear_llm_reasoning_fields() # Clear specific LLM fields
            return

        # Set header color (assuming 'urgency' might still be part of top-level or derived)
        urgency = recommendation_data.get('urgency', 'normal') # This might need to come from elsewhere
        if urgency == 'critical':
            self.recommendation_header.setStyleSheet("color: #cc0000;")
        elif urgency == 'high':
            self.recommendation_header.setStyleSheet("color: #e68a00;")
        else:
            self.recommendation_header.setStyleSheet("color: #006600;")

        # Main recommendation text (using 'reason' from top level for now, which is main_recommendation_reason)
        main_html = (
            f"<h3>Recommended Campus: {recommendation_data.get('recommended_campus_name', 'N/A')} "
            f"(ID: {recommendation_data.get('recommended_campus_id', 'N/A')})</h3>"
            f"<p><b>Confidence:</b> {recommendation_data.get('confidence_score', 0.0):.1f}%</p>"
            f"<p><b>Suggested Care Level:</b> {recommendation_data.get('recommended_level_of_care', 'N/A')}</p>"
            f"<p><b>Primary Reason:</b> {recommendation_data.get('reason', 'N/A')}</p>" # 'reason' is now main_recommendation_reason
        )
        self.main_recommendation.setHtml(main_html)

        # Populate LLM Reasoning Details
        explainability = recommendation_data.get('explainability_details', {})
        if isinstance(explainability, dict): # It should be a dict after Pydantic model_dump
            self.lbl_primary_reason.setText(explainability.get('main_recommendation_reason', "N/A"))

            key_factors = explainability.get('key_factors_considered', [])
            # Clear previous factors
            while self.factors_layout.count():
                item = self.factors_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            if key_factors:
                self.lbl_no_factors.hide()
                for factor in key_factors:
                    factor_label = QLabel(f"- {factor}")
                    factor_label.setWordWrap(True)
                    factor_label.setStyleSheet("font-size: 10pt; margin-left: 5px;")
                    self.factors_layout.addWidget(factor_label)
            else:
                self.lbl_no_factors.setText("- No specific factors listed.")
                self.lbl_no_factors.show()

            alternative_reasons = explainability.get('alternative_reasons', {})
            # Clear previous alternatives
            while self.alternatives_layout_group.count():
                item = self.alternatives_layout_group.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if alternative_reasons and isinstance(alternative_reasons, dict) and alternative_reasons:
                self.lbl_no_alternatives.hide()
                for campus, reason in alternative_reasons.items():
                    alt_label = QLabel(f"<b>{campus}:</b> {reason}")
                    alt_label.setTextFormat(Qt.RichText)
                    alt_label.setWordWrap(True)
                    alt_label.setStyleSheet("font-size: 10pt; margin-left: 5px;")
                    self.alternatives_layout_group.addWidget(alt_label)
            else:
                self.lbl_no_alternatives.setText("- No alternative considerations listed.")
                self.lbl_no_alternatives.show()
            
            confidence_exp = explainability.get('confidence_explanation')
            self.lbl_confidence_explanation.setText(confidence_exp if confidence_exp else "N/A")

        else: # explainability_details might not be a dict if something went wrong
            self.clear_llm_reasoning_fields()


        # Transport details
        transport = recommendation_data.get('transport_details', {})
        transport_html = "<ul>"
        transport_html += f"<li><b>Mode:</b> {transport.get('mode', 'N/A')}</li>"
        transport_html += f"<li><b>Estimated Time:</b> {transport.get('estimated_time_minutes', 'N/A')} minutes</li>"
        transport_html += f"<li><b>Special Requirements:</b> {transport.get('special_requirements', 'N/A')}</li>"
        transport_html += "</ul>"
        self.transport_info.setHtml(transport_html)
        
        # Conditions
        conditions = recommendation_data.get('conditions', {})
        conditions_html = "<ul>"
        conditions_html += f"<li><b>Weather:</b> {conditions.get('weather', 'N/A')}</li>"
        conditions_html += f"<li><b>Traffic:</b> {conditions.get('traffic', 'N/A')}</li>"
        conditions_html += "</ul>"
        self.conditions_info.setHtml(conditions_html)
        
        # Exclusions (This might need to be structured differently if it's complex)
        # Assuming 'exclusions_info' is a simple string or list of strings from recommendation_data for now.
        # This part might need more elaborate handling if 'exclusions' field provides structured data.
        exclusions_content = recommendation_data.get('exclusions_info', "N/A") # Placeholder for now
        self.exclusions_info.setHtml(str(exclusions_content))

        # Alternatives (This also might need more structured data)
        # The new 'alternative_reasons' is now inside explainability_details.
        # This legacy 'alternatives_info' QTextEdit might be redundant or used for other purposes.
        # For now, clearing it or using a placeholder.
        self.alternatives_info.setHtml(recommendation_data.get('legacy_alternatives_display', "Legacy alternatives: N/A"))

        # Notes (now a list of strings in the new schema)
        notes_list = recommendation_data.get('notes', [])
        if isinstance(notes_list, list) and notes_list:
            self.explanation_output.setHtml("<h3>Notes:</h3><ul>" + "".join([f"<li>{note}</li>" for note in notes_list]) + "</ul>")
        else:
            self.explanation_output.setHtml("<h3>Notes:</h3><p>N/A</p>") # Or keep legacy explanation content if any

        self.output_tabs.setCurrentIndex(0)

    def clear_llm_reasoning_fields(self):
        """Helper to clear only the LLM reasoning fields."""
        self.lbl_primary_reason.setText("N/A")
        self.lbl_confidence_explanation.setText("N/A")
        
        while self.factors_layout.count():
            child = self.factors_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.lbl_no_factors.setText("- N/A")
        self.factors_layout.addWidget(self.lbl_no_factors)
        self.lbl_no_factors.show()

        while self.alternatives_layout_group.count():
            child = self.alternatives_layout_group.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.lbl_no_alternatives.setText("- N/A")
        self.alternatives_layout_group.addWidget(self.lbl_no_alternatives)
        self.lbl_no_alternatives.show()


    def set_explanation(self, explanation_html):
        """Set the explanation HTML content. (Potentially legacy or for additional details)"""
        self.explanation_output.setHtml(explanation_html)

    def set_raw_data(self, raw_html):
        """Set the raw data HTML content."""
        self.raw_output.setHtml(raw_html)

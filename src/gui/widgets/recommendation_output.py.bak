"""
Recommendation Output Widget for the Transfer Center GUI.

This module contains the recommendation output widget used in the main application window.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QGroupBox, QHBoxLayout, QLabel, QScrollArea, QTabWidget, 
                             QTextEdit, QVBoxLayout, QWidget)
from src.core.models import Recommendation
import json
from typing import Dict, Optional

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
        
        # Clinical Scoring section
        scoring_group = QGroupBox("Clinical Scoring Details")
        scoring_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        scoring_layout = QVBoxLayout(scoring_group)
        
        self.scoring_info = QTextEdit()
        self.scoring_info.setReadOnly(True)
        self.scoring_info.setMinimumHeight(120)
        self.scoring_info.setStyleSheet(
            "background-color: #e6f2ff; border: 1px solid #adccef; border-radius: 5px; color: #000000; font-size: 11pt;"
        )
        self.scoring_info.setPlaceholderText("Clinical scoring results will appear here...")
        scoring_layout.addWidget(self.scoring_info)
        scroll_layout.addWidget(scoring_group)
        
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
        self.scoring_info.clear()
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


    def set_recommendation(self, formatted_data: Dict[str, str], raw_recommendation: Optional[Recommendation] = None):
        """Set the recommendation content.

        Args:
            formatted_data: Dictionary containing pre-formatted HTML sections for the main tab.
            raw_recommendation: The raw Recommendation object for populating detailed tabs like LLM Reasoning.
        """
        self.clear() # Clear previous content

        # Populate the main Recommendation Tab with pre-formatted HTML
        self.main_recommendation.setHtml(formatted_data.get('main', '<p>No main recommendation data available.</p>'))
        self.transport_info.setHtml(formatted_data.get('transport', '<p>No transport information available.</p>'))
        self.conditions_info.setHtml(formatted_data.get('conditions', '<p>No condition data available.</p>'))
        self.scoring_info.setHtml(formatted_data.get('scoring', '<p>No scoring data available.</p>'))
        self.exclusions_info.setHtml(formatted_data.get('exclusions', '<p>No exclusion data available.</p>'))
        self.alternatives_info.setHtml(formatted_data.get('alternatives', '<p>No alternative data available.</p>'))

        # Populate the LLM Reasoning Tab using the raw_recommendation object
        if raw_recommendation and hasattr(raw_recommendation, 'explainability_details'):
            details = getattr(raw_recommendation, 'explainability_details', None)
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except json.JSONDecodeError:
                    details = None
            
            if isinstance(details, dict):
                self.lbl_primary_reason.setText(str(details.get('main_recommendation_reason', details.get('main_reason', 'N/A'))))
                
                confidence_exp = details.get('confidence_explanation', details.get('confidence_reasoning', 'N/A'))
                self.lbl_confidence_explanation.setText(str(confidence_exp))

                # Key Factors
                key_factors = details.get('key_factors_considered', details.get('key_factors', []))
                # Clear previous factors
                while self.factors_layout.count():
                    child = self.factors_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                if isinstance(key_factors, list) and key_factors:
                    self.lbl_no_factors.hide()
                    for factor in key_factors:
                        factor_label = QLabel(f"- {factor}")
                        factor_label.setWordWrap(True)
                        self.factors_layout.addWidget(factor_label)
                else:
                    self.lbl_no_factors.setText("- No specific key factors provided.")
                    self.factors_layout.addWidget(self.lbl_no_factors)
                    self.lbl_no_factors.show()

                # Alternative Reasons / Considerations
                alt_reasons_data = details.get('alternative_reasons', details.get('alternative_considerations', {}))
                # Clear previous alternatives
                while self.alternatives_layout_group.count(): # Assuming alternatives_layout_group is the layout for these
                    child = self.alternatives_layout_group.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                if isinstance(alt_reasons_data, dict) and alt_reasons_data:
                    self.lbl_no_alternatives.hide()
                    for reason_key, reason_val in alt_reasons_data.items():
                        alt_label = QLabel(f"<b>{reason_key.replace('_', ' ').title()}:</b> {reason_val}")
                        alt_label.setWordWrap(True)
                        self.alternatives_layout_group.addWidget(alt_label)
                elif isinstance(alt_reasons_data, list) and alt_reasons_data: # Handle if it's a list of strings
                    self.lbl_no_alternatives.hide()
                    for item in alt_reasons_data:
                        alt_label = QLabel(f"- {item}")
                        alt_label.setWordWrap(True)
                        self.alternatives_layout_group.addWidget(alt_label)
                else:
                    self.lbl_no_alternatives.setText("- No alternative considerations provided.")
                    self.alternatives_layout_group.addWidget(self.lbl_no_alternatives)
                    self.lbl_no_alternatives.show()
            else:
                self.clear_llm_reasoning_fields()
        else:
            self.clear_llm_reasoning_fields()

        # Ensure the first tab (Recommendation Tab) is selected by default
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

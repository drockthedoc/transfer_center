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
        
        # Add the complete recommendation area to the tab
        recommendation_layout.addWidget(scroll_area)
        self.output_tabs.addTab(self.recommendation_tab, "Recommendation")

        # Explanation tab
        self.explanation_tab = QWidget()
        explanation_layout = QVBoxLayout(self.explanation_tab)
        explanation_layout.setContentsMargins(5, 5, 5, 5)

        self.explanation_output = QTextEdit()
        self.explanation_output.setReadOnly(True)
        self.explanation_output.setPlaceholderText(
            "Detailed explanation will appear here..."
        )
        explanation_layout.addWidget(self.explanation_output)

        self.output_tabs.addTab(self.explanation_tab, "Explanation")

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
        self.explanation_output.clear()
        self.raw_output.clear()

    def set_recommendation(self, recommendation_data):
        """Set the recommendation content with enhanced formatting.
        
        Args:
            recommendation_data: Dictionary containing recommendation sections:
                - main: Main recommendation text
                - transport: Transport and logistics information
                - conditions: Weather and traffic conditions
                - exclusions: Exclusion criteria information
                - alternatives: Alternative options
            
            Can also handle error cases where recommendation_data is a string error message.
        """
        # Handle various error cases and non-dictionary inputs
        if not isinstance(recommendation_data, dict):
            # Create an error message based on the type
            error_msg = ""
            if isinstance(recommendation_data, str):
                error_msg = recommendation_data
            elif recommendation_data is None:
                error_msg = "No recommendation data provided"
            else:
                error_msg = f"Unexpected recommendation data type: {type(recommendation_data).__name__}"
                
            # Display a formatted error message
            self.recommendation_header.setStyleSheet("color: #cc0000;")  # Red for error
            self.main_recommendation.setHtml(
                f"<p><b>Error Generating Recommendation</b></p>" 
                f"<p>{error_msg}</p>"
                f"<p>Check the application logs for more details.</p>"
            )
            # Clear other sections
            self.transport_info.setHtml("")
            self.conditions_info.setHtml("")
            self.exclusions_info.setHtml("")
            self.alternatives_info.setHtml("")
            self.output_tabs.setCurrentIndex(0)
            return
        
        # Set the header color based on urgency level
        urgency = recommendation_data.get('urgency', 'normal')
        if urgency == 'critical':
            self.recommendation_header.setStyleSheet("color: #cc0000;")  # Red for critical
        elif urgency == 'high':
            self.recommendation_header.setStyleSheet("color: #e68a00;")  # Orange for high
        else:
            self.recommendation_header.setStyleSheet("color: #006600;")  # Green for normal
            
        # Format and set the main recommendation
        main_html = recommendation_data.get('main', '')
        self.main_recommendation.setHtml(main_html)
        
        # Format and set the transport information
        transport_html = recommendation_data.get('transport', '')
        self.transport_info.setHtml(transport_html)
        
        # Format and set the weather and traffic conditions
        conditions_html = recommendation_data.get('conditions', '')
        self.conditions_info.setHtml(conditions_html)
        
        # Format and set the exclusion criteria
        exclusions_html = recommendation_data.get('exclusions', '')
        self.exclusions_info.setHtml(exclusions_html)
        
        # Format and set the alternative options
        alternatives_html = recommendation_data.get('alternatives', '')
        self.alternatives_info.setHtml(alternatives_html)
        
        # Switch to the recommendation tab
        self.output_tabs.setCurrentIndex(0)

    def set_explanation(self, explanation_html):
        """Set the explanation HTML content."""
        self.explanation_output.setHtml(explanation_html)

    def set_raw_data(self, raw_html):
        """Set the raw data HTML content."""
        self.raw_output.setHtml(raw_html)

"""
Recommendation Output Widget for the Transfer Center GUI.

This module contains the recommendation output widget used in the main application window.
"""

from PyQt5.QtWidgets import QGroupBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget


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

        # Recommendation tab
        self.recommendation_tab = QWidget()
        recommendation_layout = QVBoxLayout(self.recommendation_tab)
        recommendation_layout.setContentsMargins(5, 5, 5, 5)

        self.recommendation_output = QTextEdit()
        self.recommendation_output.setReadOnly(True)
        self.recommendation_output.setPlaceholderText(
            "Recommendation will appear here..."
        )
        recommendation_layout.addWidget(self.recommendation_output)

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
        self.recommendation_output.clear()
        self.explanation_output.clear()
        self.raw_output.clear()

    def set_recommendation(self, recommendation_html):
        """Set the recommendation HTML content."""
        self.recommendation_output.setHtml(recommendation_html)
        self.output_tabs.setCurrentIndex(0)  # Switch to recommendation tab

    def set_explanation(self, explanation_html):
        """Set the explanation HTML content."""
        self.explanation_output.setHtml(explanation_html)

    def set_raw_data(self, raw_html):
        """Set the raw data HTML content."""
        self.raw_output.setHtml(raw_html)

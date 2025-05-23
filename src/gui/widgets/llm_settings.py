"""
LLM Settings Widget for the Transfer Center GUI.

This module contains the LLM configuration settings widget used in the main application window.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LLMSettingsWidget(QWidget):
    """Widget for configuring LLM integration settings."""

    settings_changed = pyqtSignal()  # Signal when settings change
    test_connection = pyqtSignal()  # Signal to test connection
    refresh_models = pyqtSignal()  # Signal to refresh models

    def __init__(self, parent=None):
        """Initialize the LLM settings widget."""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # LLM Settings Group
        llm_group = QGroupBox("LLM Integration Settings")
        llm_layout = QFormLayout()
        llm_layout.setContentsMargins(5, 5, 5, 5)
        llm_layout.setVerticalSpacing(2)
        llm_layout.setHorizontalSpacing(5)

        # API URL input
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("http://localhost:1234/v1")
        self.api_url_input.setText("http://localhost:1234/v1")
        self.api_url_input.textChanged.connect(self.settings_changed)

        # Model selection
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        self.model_input.currentTextChanged.connect(self.settings_changed)

        # Add controls in a row
        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_input)
        
        # Refresh models button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_models)
        model_layout.addWidget(self.refresh_button)

        # Test connection button
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)

        # Status display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumHeight(100)
        self.status_display.setPlaceholderText("Connection status will appear here...")

        llm_layout.addRow("API URL:", self.api_url_input)
        llm_layout.addRow("Model:", model_layout)
        llm_layout.addRow("", self.test_button)
        llm_layout.addRow("Status:", self.status_display)

        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)

    def get_llm_settings(self):
        """Get the LLM settings from the widget."""
        return {
            "api_url": self.api_url_input.text(),
            "model": self.model_input.currentText(),
        }

    def set_models(self, models):
        """Set the available models in the dropdown."""
        current = self.model_input.currentText()
        self.model_input.clear()
        self.model_input.addItems(models)
        
        # Try to restore the previous selection if it exists
        index = self.model_input.findText(current)
        if index >= 0:
            self.model_input.setCurrentIndex(index)
        elif self.model_input.count() > 0:
            self.model_input.setCurrentIndex(0)

    def set_status(self, status_html):
        """Set the status display HTML content."""
        self.status_display.setHtml(status_html)

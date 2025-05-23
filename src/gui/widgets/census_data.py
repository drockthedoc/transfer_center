"""
Census Data Widget for the Transfer Center GUI.

This module contains the census data management widget used in the main application window.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CensusDataWidget(QWidget):
    """Widget for managing census data."""

    census_updated = pyqtSignal()  # Signal when census data is updated
    display_summary = pyqtSignal()  # Signal to display census summary

    def __init__(self, parent=None):
        """Initialize the census data widget."""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Census Data Group
        census_group = QGroupBox("Census Data")
        census_layout = QVBoxLayout()
        census_layout.setContentsMargins(5, 5, 5, 5)
        census_layout.setSpacing(3)

        # File selection row
        file_layout = QHBoxLayout()
        self.census_file_input = QLineEdit()
        self.census_file_input.setReadOnly(True)
        self.census_file_input.setPlaceholderText("Select census data file...")
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_clicked)
        
        file_layout.addWidget(self.census_file_input, 3)
        file_layout.addWidget(self.browse_button, 1)
        census_layout.addLayout(file_layout)

        # Last update info and update button row
        update_layout = QHBoxLayout()
        update_layout.addWidget(QLabel("Last Update:"))
        
        self.last_update_label = QLineEdit()
        self.last_update_label.setReadOnly(True)
        self.last_update_label.setText("Never")
        
        self.update_button = QPushButton("Update Census")
        self.update_button.clicked.connect(self.update_clicked)
        
        update_layout.addWidget(self.last_update_label, 2)
        update_layout.addWidget(self.update_button, 1)
        census_layout.addLayout(update_layout)

        # Summary button
        self.summary_button = QPushButton("Show Census Summary")
        self.summary_button.clicked.connect(self.display_summary)
        census_layout.addWidget(self.summary_button)

        # Status display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumHeight(100)
        self.status_display.setPlaceholderText("Census update status will appear here...")
        census_layout.addWidget(self.status_display)

        census_group.setLayout(census_layout)
        layout.addWidget(census_group)

    def browse_clicked(self):
        """Signal that the browse button was clicked."""
        # Using a signal would be better, but for simplicity in refactoring,
        # we'll let the main window connect a custom slot to this button
        pass

    def update_clicked(self):
        """Signal that the update button was clicked."""
        self.census_updated.emit()

    def set_file_path(self, path):
        """Set the census file path."""
        self.census_file_input.setText(path)

    def get_file_path(self):
        """Get the census file path."""
        return self.census_file_input.text()

    def set_last_update(self, timestamp):
        """Set the last update timestamp."""
        self.last_update_label.setText(timestamp)

    def set_status(self, status_html):
        """Set the status display HTML content."""
        self.status_display.setHtml(status_html)

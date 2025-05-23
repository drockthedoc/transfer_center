"""
Transport Options Widget for the Transfer Center GUI.

This module contains the transport options input widget used in the main application window.
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


class TransportOptionsWidget(QWidget):
    """Widget for inputting transport options."""

    options_changed = pyqtSignal()  # Signal when options change

    def __init__(self, parent=None):
        """Initialize the transport options widget."""
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Transport Options Group
        transport_group = QGroupBox("Transport Options")
        transport_layout = QFormLayout()
        transport_layout.setContentsMargins(5, 5, 5, 5)
        transport_layout.setVerticalSpacing(2)
        transport_layout.setHorizontalSpacing(5)

        # Transport type (EMS, Kangaroo Crew, etc.)
        self.transport_type_input = QComboBox()
        self.transport_type_input.addItems(["Local EMS", "Kangaroo Crew", "Family"])
        self.transport_type_input.currentIndexChanged.connect(self._update_transport_ui)
        self.transport_type_input.currentIndexChanged.connect(self.options_changed)

        # Transport mode (ground, helicopter, fixed-wing)
        self.transport_mode_input = QComboBox()
        self.transport_mode_input.addItems(["Ground", "Helicopter", "Fixed-Wing"])
        self.transport_mode_input.currentIndexChanged.connect(self.options_changed)

        # Estimated departure time
        self.departure_time_input = QTimeEdit()
        self.departure_time_input.setDisplayFormat("hh:mm AP")
        self.departure_time_input.timeChanged.connect(self.options_changed)

        transport_layout.addRow("Transport Type:", self.transport_type_input)
        transport_layout.addRow("Transport Mode:", self.transport_mode_input)
        transport_layout.addRow("Departure Time:", self.departure_time_input)

        transport_group.setLayout(transport_layout)
        layout.addWidget(transport_group)

    def _update_transport_ui(self, index):
        """Update transport UI elements based on selected transport type."""
        # Enable/disable transport mode selection based on transport type
        is_kc = self.transport_type_input.currentText() == "Kangaroo Crew"
        is_family = self.transport_type_input.currentText() == "Family"
        
        self.transport_mode_input.setEnabled(is_kc)
        
        if is_family:
            self.transport_mode_input.setCurrentIndex(0)  # Set to Ground

    def get_transport_data(self):
        """Get the transport options data from the widget."""
        return {
            "transport_type": self.transport_type_input.currentText(),
            "transport_mode": self.transport_mode_input.currentText(),
            "departure_time": self.departure_time_input.time().toString("hh:mm"),
        }

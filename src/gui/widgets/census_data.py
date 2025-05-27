from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QGroupBox, 
    QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt
from typing import Optional

# Actual model import
from ...core.models import BedCensus

class CensusDataWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Hospital Bed Census")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5) # Tighter margins

        census_group = QGroupBox("Current Bed Availability")
        group_layout = QFormLayout(census_group)
        group_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        group_layout.setLabelAlignment(Qt.AlignLeft)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group_layout.setSpacing(8)

        # Create labels for displaying census data
        self.general_beds_label = QLabel("N/A")
        self.icu_beds_label = QLabel("N/A")
        self.nicu_beds_label = QLabel("N/A")

        # Styling for emphasis
        font = self.general_beds_label.font()
        font.setPointSize(font.pointSize() + 1) # Slightly larger font
        self.general_beds_label.setFont(font)
        self.icu_beds_label.setFont(font)
        self.nicu_beds_label.setFont(font)

        group_layout.addRow(QLabel("<b>General Beds:</b>"), self.general_beds_label)
        group_layout.addRow(QLabel("<b>ICU Beds (incl. PICU):</b>"), self.icu_beds_label)
        group_layout.addRow(QLabel("<b>NICU Beds:</b>"), self.nicu_beds_label)

        # Add a line for visual separation if desired
        # line = QFrame()
        # line.setFrameShape(QFrame.HLine)
        # line.setFrameShadow(QFrame.Sunken)
        # group_layout.addRow(line)

        self.last_updated_label = QLabel("<i>Last updated: N/A</i>")
        self.last_updated_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        group_layout.addRow(self.last_updated_label)
        
        census_group.setLayout(group_layout)
        main_layout.addWidget(census_group)
        
        # Make the widget expand horizontally but keep a reasonable vertical size
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setLayout(main_layout)

    def update_census_data(self, census_data: Optional[BedCensus], last_updated_time: Optional[str] = None):
        if census_data:
            self.general_beds_label.setText(
                f"{getattr(census_data, 'available_beds', 'N/A')} / {getattr(census_data, 'total_beds', 'N/A')} Available"
            )
            self.icu_beds_label.setText(
                f"{getattr(census_data, 'icu_beds_available', 'N/A')} / {getattr(census_data, 'icu_beds_total', 'N/A')} Available"
            )
            self.nicu_beds_label.setText(
                f"{getattr(census_data, 'nicu_beds_available', 'N/A')} / {getattr(census_data, 'nicu_beds_total', 'N/A')} Available"
            )
        else:
            self.general_beds_label.setText("N/A")
            self.icu_beds_label.setText("N/A")
            self.nicu_beds_label.setText("N/A")

        if last_updated_time:
            self.last_updated_label.setText(f"<i>Last updated: {last_updated_time}</i>")
        else:
            from datetime import datetime
            self.last_updated_label.setText(f"<i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (local)</i>")

    def get_census_data(self) -> Optional[BedCensus]:
        # This widget is primarily for display. If it were to manage data entry for census,
        # this method would construct and return a BedCensus object.
        # For now, it doesn't hold editable census data itself.
        # It might hold a reference to the current BedCensus object if needed.
        # Returning None as it's a display widget.
        # If the main window needs to get the data that this widget is displaying,
        # it should have its own reference to the BedCensus object.
        # However, to match the previous error, let's assume it might have held some data.
        # This is a potential point of confusion from the old codebase.
        # For a clean rewrite, this widget *displays* data, it doesn't *own* or *provide* it
        # in the sense of being a source of truth for other components.
        # The main window should pass data *to* this widget.
        # If a method `get_census_data` is expected, it implies it's a source, which is tricky.
        # Let's assume it's for a scenario where this widget might be part of a form.
        # For now, returning a dummy or None.
        if hasattr(self, '_current_census_data'):
             return self._current_census_data
        return None # Or raise an error, or return a default empty BedCensus object

    def clear_display(self):
        self.update_census_data(None, "N/A")
        self.last_updated_label.setText("<i>Last updated: N/A</i>")

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    from datetime import datetime

    # Dummy BedCensus for testing
    class DummyBedCensus:
        def __init__(self, total, available, icu_total, icu_available, nicu_total, nicu_available):
            self.total_beds = total
            self.available_beds = available
            self.icu_beds_total = icu_total
            self.icu_beds_available = icu_available
            self.nicu_beds_total = nicu_total
            self.nicu_beds_available = nicu_available

    app = QApplication(sys.argv)
    CensusDataWidget.BedCensus = DummyBedCensus # Monkey patch for testing

    widget = CensusDataWidget()
    
    # Test with data
    census = DummyBedCensus(total=100, available=20, 
                            icu_total=20, icu_available=5, 
                            nicu_total=10, nicu_available=2)
    widget.update_census_data(census, datetime.now().strftime("%H:%M:%S"))
    widget.show()
    widget.resize(300, 150)

    # Test clearing
    # widget.clear_display()
    # widget.show()

    sys.exit(app.exec_())

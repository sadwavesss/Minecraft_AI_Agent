from PyQt6 import QtWidgets, QtCore, QtGui
from backend.overlay.components.base import DraggableGlassWidget
from backend.overlay.style import COLOR_GREEN, COLOR_RED, COLOR_YELLOW

class VisualizerHUD(DraggableGlassWidget):
    def __init__(self, on_settings_changed_callback, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 100)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
        self.on_settings_changed_callback = on_settings_changed_callback
        self._setup_ui()

    def _setup_ui(self):
        vis_layout = QtWidgets.QVBoxLayout(self)
        
        self.check_visualizer = QtWidgets.QCheckBox("Скрыть индикатор")
        self.check_visualizer.setChecked(False)
        self.check_visualizer.stateChanged.connect(self.on_settings_changed_callback)
        vis_layout.addWidget(self.check_visualizer)

        self.status_label = QtWidgets.QLabel("IDLE")
        self.status_label.setStyleSheet(f"color: {COLOR_GREEN}; font-weight: 900; font-size: 18px; letter-spacing: 2px;")
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vis_layout.addWidget(self.status_label)

    def set_status(self, status: str):
        self.status_label.setText(status.upper())
        if "RECORDING" in status.upper():
            color = COLOR_RED
        elif "PROCESSING" in status.upper():
            color = COLOR_YELLOW
        else:
            color = COLOR_GREEN
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 900; font-size: 18px; letter-spacing: 2px;")

    def toggle_interactive(self, interactive: bool):
        self.is_interactive = interactive
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, not interactive)
        if interactive:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
            self.check_visualizer.show()
        else:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.check_visualizer.hide()

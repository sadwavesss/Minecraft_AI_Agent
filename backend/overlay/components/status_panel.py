from PyQt6 import QtWidgets, QtGui, QtCore
from backend.overlay.components.base import GlassWidget
from backend.overlay.style import START_BUTTON_STYLE, START_BUTTON_ACTIVE_STYLE, COLOR_TEXT_MUTED

class StatusPanel(GlassWidget):
    def __init__(self, on_start_clicked_callback, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 200)
        self.on_start_clicked_callback = on_start_clicked_callback
        self._setup_ui()

    def _setup_ui(self):
        center_layout = QtWidgets.QVBoxLayout(self)
        
        self.start_button = QtWidgets.QPushButton("ЗАПУСТИТЬ СИСТЕМУ")
        self.start_button.setFixedSize(240, 60)
        self.start_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.start_button.setStyleSheet(START_BUTTON_STYLE)
        self.start_button.clicked.connect(self.on_start_clicked_callback)
        center_layout.addWidget(self.start_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.sys_status_label = QtWidgets.QLabel("СИСТЕМА ГОТОВА")
        self.sys_status_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-weight: 600; font-size: 12px;")
        center_layout.addWidget(self.sys_status_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

    def set_active(self):
        self.start_button.setText("СИСТЕМА АКТИВНА")
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet(START_BUTTON_ACTIVE_STYLE)
        self.sys_status_label.setText("СЛУШАЮ МИКРОФОН")

    def set_offline(self):
        self.sys_status_label.setText("ОФФЛАЙН")

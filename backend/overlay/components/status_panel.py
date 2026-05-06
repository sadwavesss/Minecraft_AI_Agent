from PyQt6 import QtWidgets, QtGui, QtCore
from backend.overlay.components.base import GlassWidget
from backend.overlay.style import START_BUTTON_STYLE, START_BUTTON_ACTIVE_STYLE, STOP_BUTTON_STYLE, COLOR_TEXT_MUTED

class StatusPanel(GlassWidget):
    def __init__(self, on_start_clicked_callback, on_stop_clicked_callback, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 200)
        self.on_start_clicked_callback = on_start_clicked_callback
        self.on_stop_clicked_callback = on_stop_clicked_callback
        self._setup_ui()

    def _setup_ui(self):
        center_layout = QtWidgets.QVBoxLayout(self)
        
        button_layout = QtWidgets.QHBoxLayout()
        
        self.start_button = QtWidgets.QPushButton("ЗАПУСТИТЬ")
        self.start_button.setFixedSize(140, 60)
        self.start_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.start_button.setStyleSheet(START_BUTTON_STYLE)
        self.start_button.clicked.connect(self.on_start_clicked_callback)
        button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("ОСТАНОВИТЬ")
        self.stop_button.setFixedSize(140, 60)
        self.stop_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.stop_button.setStyleSheet(STOP_BUTTON_STYLE)
        self.stop_button.clicked.connect(self.on_stop_clicked_callback)
        self.stop_button.setEnabled(False) # Изначально кнопка выключена
        button_layout.addWidget(self.stop_button)

        center_layout.addLayout(button_layout)

        self.sys_status_label = QtWidgets.QLabel("СИСТЕМА ГОТОВА")
        self.sys_status_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-weight: 600; font-size: 12px;")
        center_layout.addWidget(self.sys_status_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

    def set_active(self):
        self.start_button.setText("АКТИВНА")
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet(START_BUTTON_ACTIVE_STYLE)
        self.stop_button.setEnabled(True)
        self.sys_status_label.setText("СЛУШАЮ МИКРОФОН")

    def set_offline(self):
        self.start_button.setText("ЗАПУСТИТЬ")
        self.start_button.setEnabled(True)
        self.start_button.setStyleSheet(START_BUTTON_STYLE)
        self.stop_button.setEnabled(False)
        self.sys_status_label.setText("ОФФЛАЙН")

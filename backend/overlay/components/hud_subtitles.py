from PyQt6 import QtWidgets, QtCore, QtGui
from backend.overlay.components.base import DraggableGlassWidget
from backend.overlay.style import COLOR_TEXT_LIGHT

class SubtitlesHUD(DraggableGlassWidget):
    def __init__(self, on_settings_changed_callback, parent=None):
        super().__init__(parent)
        self.setFixedWidth(420)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
        self.on_settings_changed_callback = on_settings_changed_callback
        self._setup_ui()

    def _setup_ui(self):
        resp_layout = QtWidgets.QVBoxLayout(self)
        
        self.check_subtitles = QtWidgets.QCheckBox("Скрыть текст")
        self.check_subtitles.setChecked(False)
        self.check_subtitles.stateChanged.connect(self.on_settings_changed_callback)
        resp_layout.addWidget(self.check_subtitles)

        self.response_label = QtWidgets.QLabel("Ожидание команды...")
        self.response_label.setWordWrap(True)
        self.response_label.setStyleSheet(f"font-size: 16px; color: {COLOR_TEXT_LIGHT}; line-height: 1.6;")
        self.response_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        resp_layout.addWidget(self.response_label)

    def set_text(self, text: str):
        self.response_label.setText(text)
        self.adjustSize()

    def toggle_interactive(self, interactive: bool):
        self.is_interactive = interactive
        if interactive:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
            self.check_subtitles.show()
        else:
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            self.check_subtitles.hide()

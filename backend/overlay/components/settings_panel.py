from PyQt6 import QtWidgets, QtCore
from backend.overlay.components.base import GlassWidget
from backend.overlay.style import COLOR_PRIMARY

class SettingsPanel(GlassWidget):
    def __init__(self, on_settings_changed_callback, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.on_settings_changed_callback = on_settings_changed_callback
        self._setup_ui()

    def _setup_ui(self):
        set_layout = QtWidgets.QVBoxLayout(self)
        set_layout.setSpacing(15)

        lbl_settings = QtWidgets.QLabel("НАСТРОЙКИ АССИСТЕНТА")
        lbl_settings.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: 900; font-size: 14px; letter-spacing: 1px;")
        set_layout.addWidget(lbl_settings)

        set_layout.addWidget(QtWidgets.QLabel("Характер ИИ:"))
        self.combo_persona = QtWidgets.QComboBox()
        self.combo_persona.currentTextChanged.connect(self.on_settings_changed_callback)
        set_layout.addWidget(self.combo_persona)

        set_layout.addWidget(QtWidgets.QLabel("Голос TTS:"))
        self.combo_voice = QtWidgets.QComboBox()
        self.combo_voice.currentTextChanged.connect(self.on_settings_changed_callback)
        set_layout.addWidget(self.combo_voice)

        set_layout.addWidget(QtWidgets.QLabel("Громкость TTS:"))
        self.slider_volume = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(100)
        self.slider_volume.valueChanged.connect(self.on_settings_changed_callback)
        set_layout.addWidget(self.slider_volume)
        
        set_layout.addStretch()

    def update_data(self, personas, voices, current_persona, current_voice, volume):
        self.combo_persona.blockSignals(True)
        self.combo_voice.blockSignals(True)
        
        self.combo_persona.clear()
        self.combo_persona.addItems(personas)
        self.combo_persona.setCurrentText(current_persona)
        
        self.combo_voice.clear()
        self.combo_voice.addItems(voices)
        self.combo_voice.setCurrentText(current_voice)
        
        self.slider_volume.setValue(int(volume * 100))

        self.combo_persona.blockSignals(False)
        self.combo_voice.blockSignals(False)

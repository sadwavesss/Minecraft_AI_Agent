from PyQt6 import QtWidgets
from backend.overlay.style import COLOR_PRIMARY, COLOR_TEXT_MUTED

class HotkeyPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        hotkey_layout = QtWidgets.QHBoxLayout(self)
        hotkey_layout.setSpacing(15)

        hotkeys = [
            ("L_CTRL", "Нажми и говори (PTT)"),
            ("F2", "Настройки / Скрыть HUD")
        ]
        
        for key, desc in hotkeys:
            badge = QtWidgets.QWidget()
            badge.setStyleSheet("background: rgba(15, 23, 42, 0.6); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
            b_layout = QtWidgets.QHBoxLayout(badge)
            b_layout.setContentsMargins(10, 5, 10, 5)
            
            k_lbl = QtWidgets.QLabel(key)
            k_lbl.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: 900; font-size: 12px;")
            d_lbl = QtWidgets.QLabel(desc)
            d_lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: 600;")
            
            b_layout.addWidget(k_lbl)
            b_layout.addWidget(d_lbl)
            hotkey_layout.addWidget(badge)

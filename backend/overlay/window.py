import sys
import requests
from PyQt6 import QtWidgets, QtCore, QtGui

from backend.overlay.components.settings_panel import SettingsPanel
from backend.overlay.components.status_panel import StatusPanel
from backend.overlay.components.hotkey_panel import HotkeyPanel
from backend.overlay.components.hud_subtitles import SubtitlesHUD
from backend.overlay.components.hud_visualizer import VisualizerHUD

class OverlayWindow(QtWidgets.QWidget):
    """
    Controller class for the Fullscreen Overlay.
    Manages layout positioning, interactive states, and backend polling.
    """
    _response_signal = QtCore.pyqtSignal(str)
    _status_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Game Assistant")
        
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showFullScreen()
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self._last_response = ""
        self._is_interactive_mode = True
        self._show_subtitles = True
        self._show_visualizer = True
        self._settings_loaded = False

        self._setup_ui()

        self._response_signal.connect(self._subtitles_hud.set_text)
        self._status_signal.connect(self._visualizer_hud.set_status)

        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.timeout.connect(self._poll_backend)
        self._poll_timer.start(500)

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        if self._is_interactive_mode:
            painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 180))
        else:
            painter.fillRect(self.rect(), QtCore.Qt.GlobalColor.transparent)

    def _setup_ui(self) -> None:
        screen_geometry = QtWidgets.QApplication.primaryScreen().geometry()
        screen_w = screen_geometry.width()
        screen_h = screen_geometry.height()

        self._settings_panel = SettingsPanel(self._on_settings_changed, self)
        self._settings_panel.move(60, 60)

        self._status_panel = StatusPanel(self._on_start_clicked, self._on_stop_clicked, self)
        self._status_panel.move((screen_w - 320) // 2, (screen_h - 200) // 2)

        self._hotkey_panel = HotkeyPanel(self)
        self._hotkey_panel.adjustSize()
        self._hotkey_panel.move((screen_w - self._hotkey_panel.width()) // 2, screen_h - self._hotkey_panel.height() - 40)

        self._subtitles_hud = SubtitlesHUD(self._on_settings_changed, self)
        self._subtitles_hud.move(screen_w - 420 - 60, (screen_h - 200) // 2)

        self._visualizer_hud = VisualizerHUD(self._on_settings_changed, self)
        self._visualizer_hud.move(screen_w - 200 - 60, 60)

    def _on_start_clicked(self):
        try:
            r = requests.post("http://127.0.0.1:8000/api/start", timeout=1.0)
            if r.status_code == 200:
                self._status_panel.set_active()
        except requests.exceptions.RequestException as e:
            self._status_panel.set_offline()
            print(f"[API ERROR] Не удалось связаться с бэкендом (start): {e}")

    def _on_stop_clicked(self):
        try:
            r = requests.post("http://127.0.0.1:8000/api/stop", timeout=1.0)
            if r.status_code == 200:
                self._status_panel.set_offline()
                self._status_panel.sys_status_label.setText("ОСТАНОВЛЕНО")
        except requests.exceptions.RequestException as e:
            print(f"[API ERROR] Не удалось связаться с бэкендом (stop): {e}")

    def _load_settings_once(self):
        if self._settings_loaded:
            return
        try:
            r = requests.get("http://127.0.0.1:8000/api/settings/meta", timeout=0.5)
            r_set = requests.get("http://127.0.0.1:8000/api/settings", timeout=0.5)
            
            if r.status_code == 200 and r_set.status_code == 200:
                data = r.json()
                s_data = r_set.json()
                
                self._settings_panel.update_data(
                    data.get("personas", []),
                    data.get("voices", []),
                    s_data.get("persona", ""),
                    s_data.get("voice", ""),
                    s_data.get("volume", 1.0)
                )

                self._show_subtitles = s_data.get("show_subtitles", True)
                self._subtitles_hud.check_subtitles.setChecked(not self._show_subtitles)
                
                self._show_visualizer = s_data.get("show_visualizer", True)
                self._visualizer_hud.check_visualizer.setChecked(not self._show_visualizer)

            self._settings_loaded = True
        except requests.exceptions.RequestException as e:
            print(f"[API ERROR] Ошибка загрузки настроек: {e}")

    def _on_settings_changed(self):
        if not self._settings_loaded:
            return
            
        persona = self._settings_panel.combo_persona.currentText()
        voice = self._settings_panel.combo_voice.currentText()
        vol = self._settings_panel.slider_volume.value() / 100.0
        
        show_sub = not self._subtitles_hud.check_subtitles.isChecked()
        show_vis = not self._visualizer_hud.check_visualizer.isChecked()

        self._show_subtitles = show_sub
        self._show_visualizer = show_vis
        
        try:
            requests.post("http://127.0.0.1:8000/api/settings", json={
                "persona": persona,
                "voice": voice,
                "show_subtitles": show_sub,
                "show_visualizer": show_vis,
                "volume": vol
            }, timeout=0.5)
        except requests.exceptions.RequestException as e:
            print(f"[API ERROR] Ошибка сохранения настроек: {e}")

    def _set_mode(self, interactive: bool):
        if self._is_interactive_mode == interactive:
            return
        self._is_interactive_mode = interactive
        
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, not interactive)
        
        import sys
        if sys.platform == "win32":
            import ctypes
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            
            user32 = ctypes.windll.user32
            # В PyQt6 winId возвращает sip.voidptr, который приводится к int
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if interactive:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style & ~WS_EX_TRANSPARENT)
            else:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_TRANSPARENT)
                
        self._subtitles_hud.toggle_interactive(interactive)
        self._visualizer_hud.toggle_interactive(interactive)
        
        if interactive:
            self._settings_panel.show()
            self._status_panel.show()
            self._hotkey_panel.show()
            self._subtitles_hud.show()
            self._visualizer_hud.show()
        else:
            self._settings_panel.hide()
            self._status_panel.hide()
            self._hotkey_panel.hide()
            
            if self._show_subtitles:
                self._subtitles_hud.show()
            else:
                self._subtitles_hud.hide()
                
            if self._show_visualizer:
                self._visualizer_hud.show()
            else:
                self._visualizer_hud.hide()
                
        self.update()

    def _poll_backend(self) -> None:
        self._load_settings_once()
        
        try:
            r = requests.get("http://127.0.0.1:8000/api/latest_response", timeout=0.3)
            if r.status_code == 200:
                answer = r.json().get("answer", "")
                if answer and answer != self._last_response:
                    self._last_response = answer
                    self._response_signal.emit(answer)

            r2 = requests.get("http://127.0.0.1:8000/api/status", timeout=0.3)
            if r2.status_code == 200:
                data = r2.json()
                self._status_signal.emit(data.get("status", "IDLE"))
                
                api_show_subtitles = data.get("show_subtitles", True)
                if api_show_subtitles != self._show_subtitles:
                    self._show_subtitles = api_show_subtitles
                    self._subtitles_hud.check_subtitles.setChecked(not self._show_subtitles)
                    
                api_show_visualizer = data.get("show_visualizer", True)
                if api_show_visualizer != self._show_visualizer:
                    self._show_visualizer = api_show_visualizer
                    self._visualizer_hud.check_visualizer.setChecked(not self._show_visualizer)
                
                visible = data.get("visible", True)
                self._set_mode(visible)

        except requests.exceptions.RequestException:
            pass

def run() -> None:
    import signal
    # Позволяем Python корректно обрабатывать Ctrl+C в GUI приложении
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QtWidgets.QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run()
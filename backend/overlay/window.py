from PyQt6 import QtWidgets, QtCore, QtGui
from pynput import keyboard
import sys
import requests

try:
    import keyboard as keyboard_global
except ImportError:
    keyboard_global = None

class OverlayWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ИИ-Друг Overlay")
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 200)
        # self.hide()  # Скрыто по умолчанию (отключено, чтобы было видно сразу)
        self.show()
        self._last_toggle_time = 0
        self._toggle_cooldown = 0.3  # секунды

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Кнопка запуска
        self.is_running = False
        self.start_button = QtWidgets.QPushButton("Запустить ИИ-друга")
        self.start_button.clicked.connect(self.toggle_ai_friend)
        layout.addWidget(self.start_button)

        # Поле для ответа
        self.response_label = QtWidgets.QLabel("Готов к работе")
        self.response_label.setStyleSheet("color: white; font-size: 14px; background: rgba(0,0,0,0.7); padding: 5px;")
        self.response_label.setWordWrap(True)
        layout.addWidget(self.response_label)

        # Кнопка закрытия
        self.close_button = QtWidgets.QPushButton("Закрыть")
        self.close_button.clicked.connect(self.hide)
        layout.addWidget(self.close_button)

        # Горячая клавиша (pynput-global) + Qt-горячая клавиша + keyboard-global как резерв
        self.toggle_shortcut = QtGui.QShortcut(QtGui.QKeySequence("p"), self)
        self.toggle_shortcut.activated.connect(self.toggle_overlay)
        print("✅ Qt shortcut p зарегистрирован")

        if keyboard_global is not None:
            try:
                keyboard_global.add_hotkey('p', self.toggle_overlay)
                print("✅ keyboard (global) p зарегистрирован")
            except Exception as e:
                print(f"❌ Ошибка keyboard глобальной горячей клавиши: {e}")

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({
                '<ctrl>+<shift>+a': self.toggle_overlay
            })
            self.hotkey_listener.start()
            print("✅ pynput GlobalHotKeys p зарегистрирована")
        except Exception as e:
            print(f"❌ Ошибка регистрации pynput горячей клавиши: {e}")
            self.hotkey_listener = None

    def toggle_overlay(self):
        import time

        now = time.time()
        if now - self._last_toggle_time < self._toggle_cooldown:
            print("⏱️ Слишком быстро, пропускаем повторное переключение")
            return

        self._last_toggle_time = now
        print(f"🔄 Горячая клавиша активирована, видимо: {self.isVisible()}")
        if self.isVisible():
            self.hide()
            print("🔽 Overlay скрыт")
        else:
            self.show()
            print("🔼 Overlay показан")

    def toggle_ai_friend(self):
        if not self.is_running:
            self.start_ai_friend()
        else:
            self.stop_ai_friend()

    def start_ai_friend(self):
        self.response_label.setText("Запуск сервисов...")
        try:
            response = requests.post("http://127.0.0.1:8000/api/start")
            if response.status_code == 200:
                self.is_running = True
                self.start_button.setText("Остановить ИИ-друга")
                self.response_label.setText("ИИ-друг запущен! Говорите.")
            else:
                self.response_label.setText(f"Ошибка запуска: {response.status_code}")
        except Exception as e:
            self.response_label.setText(f"Ошибка соединения: {e}")

    def stop_ai_friend(self):
        self.response_label.setText("Остановка сервисов...")
        try:
            response = requests.post("http://127.0.0.1:8000/api/stop")
            if response.status_code == 200:
                self.is_running = False
                self.start_button.setText("Запустить ИИ-друга")
                self.response_label.setText("ИИ-друг остановлен.")
            else:
                self.response_label.setText(f"Ошибка остановки: {response.status_code}")
        except Exception as e:
            self.response_label.setText(f"Ошибка соединения: {e}")

    def show_response(self, text: str):
        self.response_label.setText(text)
        self.show()

def run_overlay_app():
    app = QtWidgets.QApplication(sys.argv)
    window = OverlayWindow()
    print("✅ Overlay приложение инициализировано")
    print("⌨️  Нажмите Ctrl+Shift+A чтобы показать/скрыть overlay")
    sys.exit(app.exec())


if __name__ == "__main__":
    run_overlay_app()

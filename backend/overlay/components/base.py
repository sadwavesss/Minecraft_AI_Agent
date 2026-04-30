from PyQt6 import QtWidgets, QtCore, QtGui
from backend.overlay.style import STYLESHEET

class GlassWidget(QtWidgets.QFrame):
    """Базовый виджет с эффектом Glassmorphism."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLESHEET)

class DraggableGlassWidget(GlassWidget):
    """Виджет, который можно перемещать мышкой в интерактивном режиме."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dragging = False
        self._drag_start_pos = QtCore.QPoint()
        self.is_interactive = True

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if self.is_interactive and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._is_dragging and self.is_interactive:
            delta = event.pos() - self._drag_start_pos
            self.move(self.pos() + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._is_dragging = False
        super().mouseReleaseEvent(event)
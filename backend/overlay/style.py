STYLESHEET = """
    GlassWidget {
        background-color: rgba(30, 30, 30, 160);
        border: 1px solid rgba(255, 255, 255, 40);
        border-radius: 15px;
    }
    QLabel {
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
        background: transparent;
    }
    QComboBox, QCheckBox {
        color: #e0e0e0;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 6px;
        padding: 5px;
        font-family: 'Segoe UI', sans-serif;
    }
    QComboBox::drop-down { border: 0px; }
    QComboBox QAbstractItemView {
        background: rgba(30, 30, 30, 240);
        color: #e0e0e0;
        selection-background-color: #6366f1;
    }
    QSlider::groove:horizontal {
        border-radius: 4px;
        height: 8px;
        background: rgba(15, 23, 42, 0.6);
    }
    QSlider::handle:horizontal {
        background: #818cf8;
        width: 16px;
        height: 16px;
        margin: -4px 0;
        border-radius: 8px;
    }
"""

START_BUTTON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #a855f7);
        color: white;
        border-radius: 12px;
        font-weight: 800;
        font-size: 15px;
        letter-spacing: 1px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    QPushButton:hover { 
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #9333ea);
        border: 1px solid rgba(255,255,255,0.3);
    }
"""

START_BUTTON_ACTIVE_STYLE = """
    background: rgba(34, 197, 94, 0.2); 
    color: #22c55e; 
    border: 1px solid #22c55e; 
    border-radius: 12px; 
    font-weight: 800;
"""

STOP_BUTTON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ef4444, stop:1 #b91c1c);
        color: white;
        border-radius: 12px;
        font-weight: 800;
        font-size: 15px;
        letter-spacing: 1px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    QPushButton:hover { 
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #dc2626, stop:1 #991b1b);
        border: 1px solid rgba(255,255,255,0.3);
    }
"""

COLOR_GREEN = "#22c55e"
COLOR_YELLOW = "#eab308"
COLOR_RED = "#ef4444"
COLOR_PRIMARY = "#818cf8"
COLOR_TEXT_MUTED = "#94a3b8"
COLOR_TEXT_LIGHT = "#f8fafc"

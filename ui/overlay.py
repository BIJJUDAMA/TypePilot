from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont

class OverlayWindow(QWidget):
    """Thread-safe PyQt6 window for displaying live transcription overlays."""
    
    # Thread-safe signals to update GUI from actor threads
    update_text_signal = pyqtSignal(str)
    update_status_signal = pyqtSignal(str)
    show_signal = pyqtSignal()
    hide_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._init_ui()
        
        # Connect signals for safe cross-thread GUI updates
        self.update_text_signal.connect(self._show_text)
        self.update_status_signal.connect(self._show_status)
        self.show_signal.connect(self.show)
        self.hide_signal.connect(self.hide)

    def _init_ui(self):
        # Configure window as frameless, stays-on-top, and non-focusable tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Build minimalist vertical layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Apple-style muted status label
        self.status_label = QLabel("Listening...")
        self.status_label.setStyleSheet("color: #8E8E93; font-weight: bold; background-color: transparent;")
        self.status_label.setFont(QFont("Segoe UI", 10))

        # Off-white main text label
        self.text_label = QLabel("")
        self.text_label.setStyleSheet("color: #F2F2F7; background-color: transparent;")
        self.text_label.setFont(QFont("Segoe UI", 12))
        self.text_label.setWordWrap(True)

        layout.addWidget(self.status_label)
        layout.addWidget(self.text_label)
        self.setLayout(layout)

        # Target only OverlayWindow by object name to prevent inheriting properties in QLabels
        self.setObjectName("OverlayWindow")
        self.setStyleSheet("""
            #OverlayWindow {
                background-color: rgba(28, 28, 30, 242); /* 95% opacity charcoal */
                border: 1px solid rgba(255, 255, 255, 20); /* 8% opacity soft boundary */
                border-radius: 10px; /* 10px border radius as requested */
                padding: 12px; /* Add padding as requested */
            }
        """)

        self.resize(450, 110)
        self._position_on_screen()

    def _position_on_screen(self):
        # Place window in the right-side bottom corner of the screen
        screen = self.screen().availableGeometry()
        x = screen.x() + screen.width() - self.width() - 40
        y = screen.y() + screen.height() - self.height() - 40
        self.move(x, y)

    @pyqtSlot(str)
    def _show_text(self, text: str):
        self.text_label.setText(text)
        self.adjustSize()
        self._position_on_screen()

    @pyqtSlot(str)
    def _show_status(self, status: str):
        self.status_label.setText(status)
        self.adjustSize()
        self._position_on_screen()

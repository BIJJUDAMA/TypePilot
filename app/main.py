import sys
from PyQt6.QtWidgets import QApplication
from core.events.bus import EventBus
from core.state_machine import AppStateMachine
from core.config import ConfigLoader
from core.platform import PlatformBridge
from core.logging import get_logger

from actors.hotkey import HotkeyActor
from actors.audio import AudioActor
from actors.whisper import WhisperActor
from actors.injection import InjectionActor
from actors.overlay import OverlayActor
from ui.overlay import OverlayWindow

class TypePilotApp:
    """Main application orchestrator integrating state, platform, actors, and UI."""
    def __init__(self):
        self.logger = get_logger("TypePilotApp")
        self.config = ConfigLoader()
        self.bus = EventBus()
        self.state_machine = AppStateMachine()
        self.bridge = PlatformBridge()
        
        # PyQt6 application context
        self.qt_app = QApplication(sys.argv)
        self.overlay_window = OverlayWindow()
        
        # Periodic timer to allow Ctrl+C signal handling on Windows
        from PyQt6.QtCore import QTimer
        self.timer = QTimer()
        self.timer.start(500)
        self.timer.timeout.connect(lambda: None)

        # Initialize actors with constructor injection
        self.actors = [
            HotkeyActor(self.bus, self.bridge, self.state_machine),
            AudioActor(self.bus, self.bridge, self.config, self.state_machine),
            WhisperActor(self.bus, self.config),
            InjectionActor(self.bus, self.bridge, self.state_machine),
            OverlayActor(self.bus, self.overlay_window)
        ]

    def start(self):
        self.logger.info("Starting TypePilot App...")
        for actor in self.actors:
            actor.start()
        self.logger.info("App Ready")
        
        # Run PyQt6 event loop
        sys.exit(self.qt_app.exec())

    def stop(self):
        self.logger.info("Shutting down...")
        for actor in self.actors:
            actor.stop()
        self.logger.info("Shutdown complete")

if __name__ == "__main__":
    app = TypePilotApp()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()

import time
from core.events.bus import EventBus
from core.state_machine import AppStateMachine
from core.config import ConfigLoader
from core.platform import PlatformBridge
from core.logging import get_logger

class TypePilotApp:
    def __init__(self):
        self.logger = get_logger("TypePilotApp")
        self.config = ConfigLoader()
        self.bus = EventBus()
        self.state_machine = AppStateMachine()
        self.bridge = PlatformBridge()
        self.actors = []

    def start(self):
        self.logger.info("Starting TypePilot Foundation...")
        # Future: Initialize actors here
        self.logger.info("Foundation Ready")

    def stop(self):
        self.logger.info("Shutting down...")
        for actor in self.actors:
            actor.stop()
        self.logger.info("Shutdown complete")

if __name__ == "__main__":
    app = TypePilotApp()
    try:
        app.start()
        # Keep alive for demo/test
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()

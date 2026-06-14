import time
from core.actor import Actor
from core.events import HOTKEY_PRESSED, HOTKEY_RELEASED
from core.state_machine.states import AppState

class HotkeyActor(Actor):
    """Listens for native hotkey press/release, transitions app state, and publishes events."""
    def __init__(self, event_bus, bridge, state_machine):
        super().__init__(event_bus)
        self.bridge = bridge
        self.state_machine = state_machine

    def start(self):
        super().start()
        self.bridge.register_hotkey(0x20, self._on_press, self._on_release)

    def stop(self):
        self.bridge.unregister_hotkey()
        super().stop()

    def _on_press(self):
        if self.state_machine.state == AppState.IDLE:
            self.logger.info("Hotkey pressed")
            try:
                self.state_machine.transition_to(AppState.LISTENING)
                self.event_bus.publish(HOTKEY_PRESSED, {"timestamp": time.time()})
            except Exception as e:
                self.logger.error(f"Failed to transition to LISTENING: {e}")

    def _on_release(self):
        if self.state_machine.state == AppState.LISTENING:
            self.logger.info("Hotkey released")
            try:
                self.state_machine.transition_to(AppState.PROCESSING)
                self.event_bus.publish(HOTKEY_RELEASED, {"timestamp": time.time()})
            except Exception as e:
                self.logger.error(f"Failed to transition to PROCESSING: {e}")

    def handle_event(self, event_type, data):
        pass

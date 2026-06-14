from core.actor import Actor
from core.events import TRANSCRIPT_FINAL, TEXT_INJECTED
from core.state_machine.states import AppState

class InjectionActor(Actor):
    """Subscribes to TRANSCRIPT_FINAL and injects text into the active window."""
    def __init__(self, event_bus, bridge, state_machine):
        super().__init__(event_bus)
        self.bridge = bridge
        self.state_machine = state_machine
        self.subscribe(TRANSCRIPT_FINAL)

    def handle_event(self, event_type, data):
        if event_type == TRANSCRIPT_FINAL:
            self._handle_transcript_final(data.get("text", ""))

    def _handle_transcript_final(self, text):
        if not text:
            # Skip injection for empty text and reset to idle
            try:
                self.state_machine.transition_to(AppState.IDLE)
            except Exception as e:
                self.logger.error(f"Error resetting to IDLE: {e}")
            return

        try:
            self.state_machine.transition_to(AppState.INJECTING)
            self.bridge.inject_text(text)
            self.event_bus.publish(TEXT_INJECTED, {"text": text})
            self.state_machine.transition_to(AppState.IDLE)
        except Exception as e:
            self.logger.error(f"Failed to inject text: {e}")
            try:
                self.state_machine.transition_to(AppState.ERROR)
                self.state_machine.transition_to(AppState.IDLE)
            except Exception as transition_err:
                self.logger.error(f"Error transitioning to IDLE from ERROR: {transition_err}")

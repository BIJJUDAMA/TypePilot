from core.actor import Actor
from core.events import TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL, HOTKEY_PRESSED, TEXT_INJECTED
from core.state_machine.states import AppState

class InjectionActor(Actor):
    """Subscribes to TRANSCRIPT_PARTIAL and TRANSCRIPT_FINAL and injects text delta into the active window."""
    def __init__(self, event_bus, bridge, state_machine):
        super().__init__(event_bus)
        self.bridge = bridge
        self.state_machine = state_machine
        self.injected_text = ""
        
        self.subscribe(HOTKEY_PRESSED)
        self.subscribe(TRANSCRIPT_PARTIAL)
        self.subscribe(TRANSCRIPT_FINAL)

    def handle_event(self, event_type, data):
        if event_type == HOTKEY_PRESSED:
            self.injected_text = ""
        elif event_type == TRANSCRIPT_PARTIAL:
            self._handle_transcript_partial(data.get("text", ""))
        elif event_type == TRANSCRIPT_FINAL:
            self._handle_transcript_final(data.get("text", ""))

    def _calculate_delta(self, old_text, new_text):
        common_prefix_len = 0
        for c1, c2 in zip(old_text, new_text):
            if c1 == c2:
                common_prefix_len += 1
            else:
                break
        backspaces = len(old_text) - common_prefix_len
        new_suffix = new_text[common_prefix_len:]
        return "\x08" * backspaces + new_suffix

    def _handle_transcript_partial(self, text):
        if not text:
            return
            
        delta = self._calculate_delta(self.injected_text, text)
        if delta:
            try:
                self.bridge.inject_text(delta)
                self.injected_text = text
            except Exception as e:
                self.logger.error(f"Failed to inject partial text: {e}")

    def _handle_transcript_final(self, text):
        delta = self._calculate_delta(self.injected_text, text)
        self.injected_text = ""
        
        if not delta:
            try:
                self.state_machine.transition_to(AppState.IDLE)
            except Exception as e:
                self.logger.error(f"Error resetting to IDLE: {e}")
            return

        try:
            self.state_machine.transition_to(AppState.INJECTING)
            self.bridge.inject_text(delta)
            self.event_bus.publish(TEXT_INJECTED, {"text": text})
            self.state_machine.transition_to(AppState.IDLE)
        except Exception as e:
            self.logger.error(f"Failed to inject final text: {e}")
            try:
                self.state_machine.transition_to(AppState.ERROR)
                self.state_machine.transition_to(AppState.IDLE)
            except Exception as transition_err:
                self.logger.error(f"Error transitioning to IDLE from ERROR: {transition_err}")

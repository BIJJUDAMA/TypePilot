from core.actor import Actor
from core.events import HOTKEY_PRESSED, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL, TEXT_INJECTED
from core.state_machine.states import AppState

class InjectionActor(Actor):
    """Subscribes to hotkey and transcript events to inject text into the active window in real-time."""
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

    def _get_diff(self, old_text, new_text):
        """Calculates the number of backspaces and suffix string to transform old_text to new_text."""
        common_len = 0
        for c1, c2 in zip(old_text, new_text):
            if c1 == c2:
                common_len += 1
            else:
                break
        backspaces = len(old_text) - common_len
        suffix = new_text[common_len:]
        return backspaces, suffix

    def _handle_transcript_partial(self, text):
        # Only inject streaming partials while in LISTENING or PROCESSING state
        if self.state_machine.state not in (AppState.LISTENING, AppState.PROCESSING):
            return

        if not text:
            return

        # Calculate difference and inject delta
        backspaces, suffix = self._get_diff(self.injected_text, text)
        if backspaces > 0 or suffix:
            injection_string = ("\u0008" * backspaces) + suffix
            try:
                self.bridge.inject_text(injection_string)
                self.injected_text = text
            except Exception as e:
                self.logger.error(f"Failed to inject partial text: {e}")

    def _handle_transcript_final(self, text):
        if not text:
            if self.injected_text:
                try:
                    self.state_machine.transition_to(AppState.INJECTING)
                    backspaces = len(self.injected_text)
                    self.bridge.inject_text("\u0008" * backspaces)
                except Exception as e:
                    self.logger.error(f"Failed to clear partial text: {e}")
            try:
                self.injected_text = ""
                self.state_machine.transition_to(AppState.IDLE)
            except Exception as e:
                self.logger.error(f"Error resetting to IDLE: {e}")
            return

        try:
            self.state_machine.transition_to(AppState.INJECTING)
            
            # Align final transcript with the last partial injected
            backspaces, suffix = self._get_diff(self.injected_text, text)
            if backspaces > 0 or suffix:
                injection_string = ("\u0008" * backspaces) + suffix
                self.bridge.inject_text(injection_string)
            
            self.event_bus.publish(TEXT_INJECTED, {"text": text})
            self.injected_text = ""
            self.state_machine.transition_to(AppState.IDLE)
        except Exception as e:
            self.logger.error(f"Failed to inject final text: {e}")
            self.injected_text = ""
            try:
                self.state_machine.transition_to(AppState.ERROR)
                self.state_machine.transition_to(AppState.IDLE)
            except Exception as transition_err:
                self.logger.error(f"Error transitioning to IDLE from ERROR: {transition_err}")

import threading
from core.actor import Actor
from core.events import HOTKEY_PRESSED, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL, TEXT_INJECTED, ERROR

class OverlayActor(Actor):
    """Listens to transcription/status events and updates the OverlayWindow GUI thread-safely."""
    def __init__(self, event_bus, overlay_window):
        super().__init__(event_bus)
        self.window = overlay_window
        
        self.subscribe(HOTKEY_PRESSED)
        self.subscribe(TRANSCRIPT_PARTIAL)
        self.subscribe(TRANSCRIPT_FINAL)
        self.subscribe(TEXT_INJECTED)
        self.subscribe(ERROR)

    def handle_event(self, event_type, data):
        if event_type == HOTKEY_PRESSED:
            self.window.update_text_signal.emit("")
            self.window.update_status_signal.emit("Listening...")
            self.window.show_signal.emit()
            
        elif event_type == TRANSCRIPT_PARTIAL:
            self.window.update_text_signal.emit(data.get("text", ""))
            
        elif event_type == TRANSCRIPT_FINAL:
            self.window.update_text_signal.emit(data.get("text", ""))
            self.window.update_status_signal.emit("Processing...")
            
        elif event_type == TEXT_INJECTED:
            self.window.hide_signal.emit()
            
        elif event_type == ERROR:
            self.window.update_status_signal.emit("Error")
            self.window.update_text_signal.emit(data.get("message", "An error occurred"))
            self.window.show_signal.emit()
            # Auto-hide error overlay after 3 seconds
            threading.Timer(3.0, self.window.hide_signal.emit).start()

import array
import threading
import time
from core.actor import Actor
from core.events import HOTKEY_PRESSED, HOTKEY_RELEASED, AUDIO_CHUNK
from core.state_machine.states import AppState

class AudioActor(Actor):
    """Manages audio recording session, pulling samples from bridge and publishing them."""
    def __init__(self, event_bus, bridge, config, state_machine):
        super().__init__(event_bus)
        self.bridge = bridge
        self.config = config
        self.state_machine = state_machine
        self.is_recording = False
        self.poll_thread = None
        self.chunk_sec = self.config.get("audio.chunk_ms", 20) / 1000.0

        self.subscribe(HOTKEY_PRESSED)
        self.subscribe(HOTKEY_RELEASED)

    def handle_event(self, event_type, data):
        if event_type == HOTKEY_PRESSED:
            self._start_recording()
        elif event_type == HOTKEY_RELEASED:
            self._stop_recording()

    def _start_recording(self):
        if self.is_recording:
            return
        self.is_recording = True
        try:
            self.bridge.start_audio_capture()
            self.poll_thread = threading.Thread(target=self._poll_audio, daemon=True)
            self.poll_thread.start()
            self.logger.info("Audio recording started")
        except Exception as e:
            self.logger.error(f"Failed to start audio: {e}")
            self.is_recording = False
            try:
                self.state_machine.transition_to(AppState.ERROR)
            except Exception:
                pass

    def _stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        if self.poll_thread:
            self.poll_thread.join(timeout=1.0)
        try:
            self.bridge.stop_audio_capture()
            final_samples = self.bridge.get_audio_samples()
            if final_samples:
                audio_bytes = array.array('f', final_samples).tobytes()
                self.event_bus.publish(AUDIO_CHUNK, {"audio": audio_bytes})
            self.logger.info("Audio recording stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop audio: {e}")
            try:
                self.state_machine.transition_to(AppState.ERROR)
            except Exception:
                pass

    def _poll_audio(self):
        while self.is_recording:
            try:
                samples = self.bridge.get_audio_samples()
                if samples:
                    audio_bytes = array.array('f', samples).tobytes()
                    self.event_bus.publish(AUDIO_CHUNK, {"audio": audio_bytes})
            except Exception as e:
                self.logger.error(f"Error polling audio: {e}")
            time.sleep(self.chunk_sec)

    def stop(self):
        self._stop_recording()
        super().stop()

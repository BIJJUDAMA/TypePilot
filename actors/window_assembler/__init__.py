import numpy as np
from core.actor import Actor
from core.events import HOTKEY_PRESSED, HOTKEY_RELEASED, AUDIO_CHUNK, AUDIO_WINDOW_READY

class WindowAssemblerActor(Actor):
    """Buffers incoming audio chunks and emits overlapping sliding windows."""
    def __init__(self, event_bus, config):
        super().__init__(event_bus)
        self.config = config
        
        self.window_size_sec = self.config.get("whisper.window_size_sec", 2.0)
        self.step_size_sec = self.config.get("whisper.step_size_sec", 0.5)
        self.sample_rate = self.config.get("audio.sample_rate", 16000)
        
        self.window_size_samples = int(self.window_size_sec * self.sample_rate)
        self.step_size_samples = int(self.step_size_sec * self.sample_rate)
        
        self.audio_buffer = []
        self.samples_since_last_window = 0
        self.is_active = False
        
        self.subscribe(HOTKEY_PRESSED)
        self.subscribe(HOTKEY_RELEASED)
        self.subscribe(AUDIO_CHUNK)

    def handle_event(self, event_type, data):
        if event_type == HOTKEY_PRESSED:
            self._handle_hotkey_pressed()
        elif event_type == AUDIO_CHUNK:
            self._handle_audio_chunk(data["audio"])
        elif event_type == HOTKEY_RELEASED:
            self._handle_hotkey_released()

    def _handle_hotkey_pressed(self):
        self.audio_buffer = []
        self.samples_since_last_window = 0
        self.is_active = True
        self.logger.info("Window Assembler activated")

    def _handle_audio_chunk(self, audio_bytes):
        if not self.is_active:
            return
        
        chunk = np.frombuffer(audio_bytes, dtype=np.float32)
        self.audio_buffer.append(chunk)
        self.samples_since_last_window += len(chunk)
        
        # Periodically emit sliding window
        if self.samples_since_last_window >= self.step_size_samples:
            self.samples_since_last_window = 0
            self._emit_window(is_final=False)

    def _handle_hotkey_released(self):
        if not self.is_active:
            return
        self.is_active = False
        # Emit final window containing the remaining audio
        self._emit_window(is_final=True)
        self.logger.info("Window Assembler finalized")

    def _emit_window(self, is_final=False):
        if not self.audio_buffer:
            self.event_bus.publish(AUDIO_WINDOW_READY, {
                "audio": b"",
                "is_final": is_final
            })
            return
            
        try:
            audio_data = np.concatenate(self.audio_buffer)
            
            # Slice to window size if it exceeds it
            if len(audio_data) > self.window_size_samples:
                audio_data = audio_data[-self.window_size_samples:]
            
            # Convert to bytes
            audio_bytes = audio_data.tobytes()
            self.event_bus.publish(AUDIO_WINDOW_READY, {
                "audio": audio_bytes,
                "is_final": is_final
            })
        except Exception as e:
            self.logger.error(f"Error emitting audio window: {e}")
            if is_final:
                self.event_bus.publish(AUDIO_WINDOW_READY, {
                    "audio": b"",
                    "is_final": True
                })

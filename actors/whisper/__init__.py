import numpy as np
from faster_whisper import WhisperModel
from core.actor import Actor
from core.events import AUDIO_CHUNK, HOTKEY_RELEASED, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL

class WhisperActor(Actor):
    """Processes raw audio chunks using faster-whisper, generating partial and final transcripts."""
    def __init__(self, event_bus, config):
        super().__init__(event_bus)
        self.config = config
        
        # Load model once at startup
        model_size = self.config.get("whisper.model", "small")
        self.model = WhisperModel(model_size, device="cpu", compute_type="float32")
        self.logger.info(f"Loaded faster-whisper model: {model_size}")
        
        self.audio_buffer = []
        self.chunks_since_last_partial = 0
        
        self.subscribe(AUDIO_CHUNK)
        self.subscribe(HOTKEY_RELEASED)

    def handle_event(self, event_type, data):
        if event_type == AUDIO_CHUNK:
            self._handle_audio_chunk(data["audio"])
        elif event_type == HOTKEY_RELEASED:
            self._handle_hotkey_released()

    def _handle_audio_chunk(self, audio_bytes):
        # Convert float32 bytes back to numpy array
        chunk = np.frombuffer(audio_bytes, dtype=np.float32)
        self.audio_buffer.append(chunk)
        self.chunks_since_last_partial += 1
        
        # Periodically generate partial transcript (every ~500ms = 25 chunks * 20ms)
        if self.chunks_since_last_partial >= 25:
            self.chunks_since_last_partial = 0
            self._generate_partial_transcript()

    def _generate_partial_transcript(self):
        if not self.audio_buffer:
            return
        try:
            audio_data = np.concatenate(self.audio_buffer)
            # Run fast transcription for partial feedback
            segments, _ = self.model.transcribe(audio_data, beam_size=1)
            text = " ".join([seg.text for seg in segments]).strip()
            if text:
                self.event_bus.publish(TRANSCRIPT_PARTIAL, {"text": text})
        except Exception as e:
            self.logger.error(f"Error transcribing partial: {e}")

    def _handle_hotkey_released(self):
        if not self.audio_buffer:
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})
            return
        
        try:
            audio_data = np.concatenate(self.audio_buffer)
            self.audio_buffer.clear()
            self.chunks_since_last_partial = 0
            
            # Run full transcription on release
            segments, _ = self.model.transcribe(audio_data, beam_size=5)
            text = " ".join([seg.text for seg in segments]).strip()
            self.logger.info(f"Final transcript: '{text}'")
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": text})
        except Exception as e:
            self.logger.error(f"Error transcribing final: {e}")
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})

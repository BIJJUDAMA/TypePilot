import numpy as np
from faster_whisper import WhisperModel
from core.actor import Actor
from core.events import AUDIO_WINDOW_READY, TRANSCRIPT_SEGMENT

class WhisperActor(Actor):
    """Processes audio windows using faster-whisper, generating transcript segments."""
    def __init__(self, event_bus, config):
        super().__init__(event_bus)
        self.config = config
        
        # Load model once at startup with optimized int8 quantization on CPU
        model_size = self.config.get("whisper.model", "small")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = self.config.get("whisper.language", "en")
        self.logger.info(f"Loaded faster-whisper model: {model_size} (int8 CPU, language: {self.language})")
        
        self.subscribe(AUDIO_WINDOW_READY)

    def handle_event(self, event_type, data):
        if event_type == AUDIO_WINDOW_READY:
            self._handle_audio_window(data["audio"], data.get("is_final", False))

    def _handle_audio_window(self, audio_bytes, is_final):
        if not audio_bytes:
            self.event_bus.publish(TRANSCRIPT_SEGMENT, {
                "text": "",
                "is_final": is_final
            })
            return
            
        try:
            audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
            
            # Use higher beam size for the final transcription segment
            beam_size = 5 if is_final else 1
            
            segments, _ = self.model.transcribe(
                audio_data,
                beam_size=beam_size,
                vad_filter=True,
                language=self.language,
                temperature=0.0
            )
            text = " ".join([seg.text for seg in segments]).strip()
            
            self.event_bus.publish(TRANSCRIPT_SEGMENT, {
                "text": text,
                "is_final": is_final
            })
        except ValueError as e:
            if "max() iterable argument is empty" in str(e):
                # VAD filter cleared all audio (silence)
                self.event_bus.publish(TRANSCRIPT_SEGMENT, {
                    "text": "",
                    "is_final": is_final
                })
            else:
                self.logger.error(f"Error transcribing: {e}")
                self.event_bus.publish(TRANSCRIPT_SEGMENT, {
                    "text": "",
                    "is_final": is_final
                })
        except Exception as e:
            self.logger.error(f"Error transcribing: {e}")
            self.event_bus.publish(TRANSCRIPT_SEGMENT, {
                "text": "",
                "is_final": is_final
            })

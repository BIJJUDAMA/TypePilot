import numpy as np
from faster_whisper import WhisperModel
from core.actor import Actor
from core.events import AUDIO_CHUNK, HOTKEY_RELEASED, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL

class WhisperActor(Actor):
    """Processes raw audio chunks using faster-whisper, generating partial and final transcripts."""
    def __init__(self, event_bus, config):
        super().__init__(event_bus)
        self.config = config
        
        # Load model once at startup with optimized int8 quantization on CPU
        model_size = self.config.get("whisper.model", "small")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = self.config.get("whisper.language", "en")
        self.logger.info(f"Loaded faster-whisper model: {model_size} (int8 CPU, language: {self.language})")
        
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
            # Only run partial transcription if the queue is empty to prevent lagging behind
            if self.queue.qsize() == 0:
                self._generate_partial_transcript()

    def _generate_partial_transcript(self):
        if not self.audio_buffer:
            return
        try:
            audio_data = np.concatenate(self.audio_buffer)
            # Only transcribe the last 3 seconds (48,000 samples at 16kHz) for partials to avoid O(N^2) lag
            audio_data_partial = audio_data[-48000:]
            
            # Run fast transcription with strict decoding parameters
            segments, _ = self.model.transcribe(
                audio_data_partial,
                beam_size=1,
                vad_filter=True,
                language=self.language,
                temperature=0.0
            )
            text = " ".join([seg.text for seg in segments]).strip()
            if text:
                self.event_bus.publish(TRANSCRIPT_PARTIAL, {"text": text})
        except ValueError as e:
            if "max() iterable argument is empty" in str(e):
                # Silently ignore when VAD filters out all audio (no speech detected)
                pass
            else:
                self.logger.error(f"Error transcribing partial: {e}")
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
            
            # Run full transcription on release with strict parameters
            segments, _ = self.model.transcribe(
                audio_data,
                beam_size=5,
                vad_filter=True,
                language=self.language,
                temperature=0.0
            )
            text = " ".join([seg.text for seg in segments]).strip()
            self.logger.info(f"Final transcript: '{text}'")
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": text})
        except ValueError as e:
            if "max() iterable argument is empty" in str(e):
                self.logger.info("Final transcript: (no speech detected)")
                self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})
            else:
                self.logger.error(f"Error transcribing final: {e}")
                self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})
        except Exception as e:
            self.logger.error(f"Error transcribing final: {e}")
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})

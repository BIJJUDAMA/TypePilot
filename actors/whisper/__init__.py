import numpy as np
import threading
from faster_whisper import WhisperModel
from core.actor import Actor
from core.events import AUDIO_CHUNK, HOTKEY_RELEASED, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL

class WhisperActor(Actor):
    """Processes session-based growing audio buffer using faster-whisper, generating partial and final transcripts."""
    def __init__(self, event_bus, config):
        super().__init__(event_bus)
        self.config = config
        
        # Load model once at startup with optimized int8 quantization on CPU
        model_size = self.config.get("whisper.model", "small")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = self.config.get("whisper.language", "en")
        self.logger.info(f"Loaded faster-whisper model: {model_size} (int8 CPU, language: {self.language})")
        
        self.audio_buffer = []
        self.buffer_lock = threading.Lock()
        self.silent_chunks_count = 0
        self.is_silent = True
        self.chunks_received_since_last_transcribe = 0
        self.transcribing = False
        
        self.subscribe(AUDIO_CHUNK)
        self.subscribe(HOTKEY_RELEASED)

    def handle_event(self, event_type, data):
        if event_type == AUDIO_CHUNK:
            self._handle_audio_chunk(data["audio"])
        elif event_type == HOTKEY_RELEASED:
            self._handle_hotkey_released()

    def _handle_audio_chunk(self, audio_bytes):
        if not audio_bytes:
            return
            
        try:
            samples = np.frombuffer(audio_bytes, dtype=np.float32)
            if len(samples) == 0:
                return
                
            # RMS-based Silence Detection
            rms = np.sqrt(np.mean(samples ** 2))
            if rms < 0.006:
                self.silent_chunks_count += 1
            else:
                self.silent_chunks_count = 0
                self.is_silent = False
                
            if self.silent_chunks_count >= 50: # 50 chunks * 20ms = 1.0 second
                self.is_silent = True
                
            with self.buffer_lock:
                self.audio_buffer.extend(samples)
                
            self.chunks_received_since_last_transcribe += 1
            if self.chunks_received_since_last_transcribe >= 25: # 25 chunks * 20ms = 500ms
                self.chunks_received_since_last_transcribe = 0
                if not self.is_silent and not self.transcribing:
                    self._run_async_transcription()
                    
        except Exception as e:
            self.logger.error(f"Error handling audio chunk: {e}")

    def _run_async_transcription(self):
        with self.buffer_lock:
            if not self.audio_buffer:
                return
            # Slice the last 3.0 seconds (48,000 samples at 16kHz) for context window
            context_samples = self.audio_buffer[-48000:]
            audio_copy = np.array(context_samples, dtype=np.float32)
            
        if len(audio_copy) < 160: # less than 10ms, skip
            return
            
        self.transcribing = True
        thread = threading.Thread(target=self._transcribe_async_worker, args=(audio_copy,))
        thread.daemon = True
        thread.start()

    def _transcribe_async_worker(self, audio_data):
        try:
            segments, _ = self.model.transcribe(
                audio_data,
                beam_size=1,
                vad_filter=True,
                language=self.language,
                temperature=0.0
            )
            text = " ".join([seg.text for seg in segments]).strip()
            self.event_bus.publish(TRANSCRIPT_PARTIAL, {"text": text})
        except ValueError as e:
            if "max() iterable argument is empty" in str(e):
                # VAD filter cleared all audio (silence)
                self.event_bus.publish(TRANSCRIPT_PARTIAL, {"text": ""})
            else:
                self.logger.error(f"ValueError in async transcription: {e}")
        except Exception as e:
            self.logger.error(f"Error in async transcription: {e}")
        finally:
            self.transcribing = False

    def _handle_hotkey_released(self):
        with self.buffer_lock:
            audio_data = np.array(self.audio_buffer, dtype=np.float32)
            self.audio_buffer = []
            self.silent_chunks_count = 0
            self.is_silent = True
            self.chunks_received_since_last_transcribe = 0
            
        if len(audio_data) < 160:
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})
            return
            
        try:
            segments, _ = self.model.transcribe(
                audio_data,
                beam_size=5,
                vad_filter=True,
                language=self.language,
                temperature=0.0
            )
            text = " ".join([seg.text for seg in segments]).strip()
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": text})
        except ValueError as e:
            if "max() iterable argument is empty" in str(e):
                self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})
            else:
                self.logger.error(f"ValueError in final transcription: {e}")
                self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})
        except Exception as e:
            self.logger.error(f"Error in final transcription: {e}")
            self.event_bus.publish(TRANSCRIPT_FINAL, {"text": ""})

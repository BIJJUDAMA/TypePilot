import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from core.events import AUDIO_CHUNK, HOTKEY_RELEASED, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL
from actors.whisper import WhisperActor

class TestWhisperActor(unittest.TestCase):
    @patch('actors.whisper.WhisperModel')
    def setUp(self, mock_model_class):
        self.bus = MagicMock()
        self.config = MagicMock()
        self.config.get.side_effect = lambda key, default: default
        
        # Set up WhisperActor with mocked model class
        self.actor = WhisperActor(self.bus, self.config)
        self.mock_model = self.actor.model
        
        # Set default transcribe return value to avoid unpack exceptions
        mock_segment = MagicMock()
        mock_segment.text = "hello"
        self.mock_model.transcribe.return_value = ([mock_segment], None)

    def test_audio_chunk_accumulation(self):
        # Feed one chunk (20ms = 320 float32 samples at 16kHz)
        samples = [0.1] * 320
        audio_bytes = np.array(samples, dtype=np.float32).tobytes()
        
        self.actor.handle_event(AUDIO_CHUNK, {"audio": audio_bytes})
        
        # Check that samples are in the buffer
        with self.actor.buffer_lock:
            self.assertEqual(len(self.actor.audio_buffer), 320)
            np.testing.assert_allclose(self.actor.audio_buffer, samples)

    @patch('threading.Thread')
    def test_periodic_transcription_triggered(self, mock_thread_class):
        # We want to check that transcription is triggered asynchronously after 25 chunks
        mock_segment = MagicMock()
        mock_segment.text = "hello"
        self.mock_model.transcribe.return_value = ([mock_segment], None)
        
        active_bytes = np.array([0.1] * 320, dtype=np.float32).tobytes()
        
        # Send 24 chunks - should not trigger yet
        for _ in range(24):
            self.actor.handle_event(AUDIO_CHUNK, {"audio": active_bytes})
        mock_thread_class.assert_not_called()
        
        # Send the 25th chunk
        self.actor.handle_event(AUDIO_CHUNK, {"audio": active_bytes})
        mock_thread_class.assert_called_once()

    def test_silence_with_vad_filter_empty_partial(self):
        # Test that if VAD raises max() iterable error, empty partial is published
        self.mock_model.transcribe.side_effect = ValueError("max() iterable argument is empty")
        
        # Run worker directly
        self.actor._transcribe_async_worker(np.array([0.0] * 320, dtype=np.float32))
        
        self.bus.publish.assert_called_once_with(TRANSCRIPT_PARTIAL, {"text": ""})

    def test_silence_with_vad_filter_empty_final(self):
        # Test that if final transcription raises max() iterable error, empty final is published
        self.mock_model.transcribe.side_effect = ValueError("max() iterable argument is empty")
        
        # Accumulate audio and release hotkey
        active_bytes = np.array([0.0] * 320, dtype=np.float32).tobytes()
        self.actor.handle_event(AUDIO_CHUNK, {"audio": active_bytes})
        self.actor.handle_event(HOTKEY_RELEASED, {})
        
        self.bus.publish.assert_called_once_with(TRANSCRIPT_FINAL, {"text": ""})

    def test_hotkey_released_final_transcription(self):
        mock_segment = MagicMock()
        mock_segment.text = "hello world"
        self.mock_model.transcribe.return_value = ([mock_segment], None)
        
        # Accumulate some audio
        active_bytes = np.array([0.1] * 320, dtype=np.float32).tobytes()
        self.actor.handle_event(AUDIO_CHUNK, {"audio": active_bytes})
        
        # Release hotkey
        self.actor.handle_event(HOTKEY_RELEASED, {})
        
        # Verify final transcription ran with beam_size=5
        self.mock_model.transcribe.assert_called_once()
        args, kwargs = self.mock_model.transcribe.call_args
        self.assertEqual(kwargs.get("beam_size"), 5)
        
        # Verify TRANSCRIPT_FINAL published
        self.bus.publish.assert_called_once_with(TRANSCRIPT_FINAL, {"text": "hello world"})
        
        # Verify buffer is cleared
        with self.actor.buffer_lock:
            self.assertEqual(len(self.actor.audio_buffer), 0)

import array
import unittest
from unittest.mock import MagicMock, patch
from core.events import AUDIO_WINDOW_READY, TRANSCRIPT_SEGMENT
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

    def test_audio_accumulation_and_transcription(self):
        mock_segment = MagicMock()
        mock_segment.text = "hello world"
        self.mock_model.transcribe.return_value = ([mock_segment], None)

        # Feed 1 window with is_final=True
        audio_bytes = array.array('f', [0.1] * 160).tobytes()
        self.actor.handle_event(AUDIO_WINDOW_READY, {"audio": audio_bytes, "is_final": True})
        
        # Verify transcription called and correct transcript segment published
        self.mock_model.transcribe.assert_called_once()
        self.bus.publish.assert_called_once_with(TRANSCRIPT_SEGMENT, {"text": "hello world", "is_final": True})

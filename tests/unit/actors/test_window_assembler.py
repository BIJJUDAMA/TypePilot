import array
import unittest
from unittest.mock import MagicMock
from core.events import AUDIO_CHUNK, HOTKEY_PRESSED, HOTKEY_RELEASED, AUDIO_WINDOW_READY
from actors.window_assembler import WindowAssemblerActor

class TestWindowAssemblerActor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.config = MagicMock()
        # Mock config values
        self.config.get.side_effect = lambda key, default: {
            "whisper.window_size_sec": 2.0,
            "whisper.step_size_sec": 0.5,
            "audio.sample_rate": 16000
        }.get(key, default)
        
        self.actor = WindowAssemblerActor(self.bus, self.config)

    def test_window_accumulation_and_release(self):
        # 1. Start session
        self.actor.handle_event(HOTKEY_PRESSED, {})
        self.assertTrue(self.actor.is_active)
        
        # 2. Feed audio chunks.
        # step size is 0.5 sec = 8000 samples.
        # Send 8000 samples total.
        # Send 50 chunks of 160 samples (each 10ms of audio, 8000 samples total)
        chunk_bytes = array.array('f', [0.1] * 160).tobytes()
        for _ in range(50):
            self.actor.handle_event(AUDIO_CHUNK, {"audio": chunk_bytes})
            
        # Verify that AUDIO_WINDOW_READY was published
        self.bus.publish.assert_called_with(AUDIO_WINDOW_READY, {
            "audio": unittest.mock.ANY,
            "is_final": False
        })
        
        # 3. Release hotkey
        self.bus.publish.reset_mock()
        self.actor.handle_event(HOTKEY_RELEASED, {})
        
        # Verify final window emitted
        self.bus.publish.assert_called_once_with(AUDIO_WINDOW_READY, {
            "audio": unittest.mock.ANY,
            "is_final": True
        })
        self.assertFalse(self.actor.is_active)

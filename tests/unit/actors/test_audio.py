import array
import time
import unittest
from unittest.mock import MagicMock
from core.events import HOTKEY_PRESSED, HOTKEY_RELEASED, AUDIO_CHUNK
from core.state_machine.states import AppState
from actors.audio import AudioActor

class TestAudioActor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.bridge = MagicMock()
        self.config = MagicMock()
        self.config.get.side_effect = lambda key, default: default if key == "audio.chunk_ms" else None
        self.state_machine = MagicMock()
        
        self.actor = AudioActor(self.bus, self.bridge, self.config, self.state_machine)

    def test_hotkey_pressed_starts_recording(self):
        self.bridge.get_audio_samples.return_value = [0.5, -0.5]
        
        # Trigger hotkey pressed
        self.actor.handle_event(HOTKEY_PRESSED, {"timestamp": time.time()})
        self.assertTrue(self.actor.is_recording)
        self.bridge.start_audio_capture.assert_called_once()

        # Let the poll thread run briefly
        time.sleep(0.1)
        
        # Trigger hotkey released
        self.actor.handle_event(HOTKEY_RELEASED, {"timestamp": time.time()})
        self.assertFalse(self.actor.is_recording)
        self.bridge.stop_audio_capture.assert_called_once()

        # Check that AUDIO_CHUNK was published with expected float32 bytes
        self.bus.publish.assert_any_call(
            AUDIO_CHUNK, 
            {"audio": array.array('f', [0.5, -0.5]).tobytes()}
        )
        self.actor.stop()

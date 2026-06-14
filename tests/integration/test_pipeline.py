import array
import time
import unittest
from unittest.mock import MagicMock, patch
from core.events.bus import EventBus
from core.state_machine import AppStateMachine
from core.state_machine.states import AppState
from core.events import TEXT_INJECTED
from actors.hotkey import HotkeyActor
from actors.audio import AudioActor
from actors.window_assembler import WindowAssemblerActor
from actors.whisper import WhisperActor
from actors.transcript_assembler import TranscriptAssemblerActor
from actors.injection import InjectionActor
from actors.overlay import OverlayActor

class TestPipelineIntegration(unittest.TestCase):
    @patch('actors.whisper.WhisperModel')
    def test_complete_dictation_pipeline(self, mock_whisper_model_class):
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "hello from integration test"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_whisper_model_class.return_value = mock_model

        bus = EventBus()
        state_machine = AppStateMachine()
        bridge = MagicMock()
        config = MagicMock()
        
        config.get.side_effect = lambda key, default: 10 if key == "audio.chunk_ms" else default

        # Safe sample generator function to prevent StopIteration
        sample_chunk = [0.1] * 160
        sample_delivered = False
        def get_samples_mock():
            nonlocal sample_delivered
            if not sample_delivered:
                sample_delivered = True
                return sample_chunk
            return []

        bridge.get_audio_samples.side_effect = get_samples_mock

        # Setup actors
        hotkey_actor = HotkeyActor(bus, bridge, state_machine)
        audio_actor = AudioActor(bus, bridge, config, state_machine)
        window_assembler = WindowAssemblerActor(bus, config)
        whisper_actor = WhisperActor(bus, config)
        transcript_assembler = TranscriptAssemblerActor(bus)
        injection_actor = InjectionActor(bus, bridge, state_machine)
        
        mock_window = MagicMock()
        overlay_actor = OverlayActor(bus, mock_window)

        hotkey_actor.start()
        audio_actor.start()
        window_assembler.start()
        whisper_actor.start()
        transcript_assembler.start()
        injection_actor.start()
        overlay_actor.start()

        injected_event_data = None
        def on_injected(data):
            nonlocal injected_event_data
            injected_event_data = data

        bus.subscribe(TEXT_INJECTED, on_injected)

        # Retrieve hotkey trigger callbacks
        reg_args = bridge.register_hotkey.call_args[0]
        on_press = reg_args[1]
        on_release = reg_args[2]

        on_press()
        time.sleep(0.05)
        self.assertEqual(state_machine.state, AppState.LISTENING)

        # Trigger hotkey release
        on_release()
        
        # Wait up to 1.5 seconds for injection
        start_time = time.time()
        while injected_event_data is None and (time.time() - start_time) < 1.5:
            time.sleep(0.05)

        self.assertEqual(state_machine.state, AppState.IDLE)
        bridge.inject_text.assert_called_once_with("hello from integration test")
        self.assertIsNotNone(injected_event_data)
        self.assertEqual(injected_event_data["text"], "hello from integration test")

        hotkey_actor.stop()
        audio_actor.stop()
        window_assembler.stop()
        whisper_actor.stop()
        transcript_assembler.stop()
        injection_actor.stop()
        overlay_actor.stop()

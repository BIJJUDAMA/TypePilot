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
from actors.whisper import WhisperActor
from actors.injection import InjectionActor
from actors.overlay import OverlayActor

class TestAppStabilityStress(unittest.TestCase):
    @patch('actors.whisper.WhisperModel')
    def test_stress_100_dictations(self, mock_whisper_model_class):
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "stress test utterance"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_whisper_model_class.return_value = mock_model

        bus = EventBus()
        state_machine = AppStateMachine()
        bridge = MagicMock()
        config = MagicMock()
        
        config.get.side_effect = lambda key, default: 10 if key == "audio.chunk_ms" else default

        # Create active actors
        hotkey_actor = HotkeyActor(bus, bridge, state_machine)
        audio_actor = AudioActor(bus, bridge, config, state_machine)
        whisper_actor = WhisperActor(bus, config)
        injection_actor = InjectionActor(bus, bridge, state_machine)
        
        mock_window = MagicMock()
        overlay_actor = OverlayActor(bus, mock_window)

        hotkey_actor.start()
        audio_actor.start()
        whisper_actor.start()
        injection_actor.start()
        overlay_actor.start()

        # Run 100 dictation cycles
        for i in range(100):
            injected_event_data = None
            def on_injected(data):
                nonlocal injected_event_data
                injected_event_data = data

            unsub = bus.subscribe(TEXT_INJECTED, on_injected)

            # Setup samples to return a single chunk for this cycle
            sample_delivered = False
            def get_samples_mock():
                nonlocal sample_delivered
                if not sample_delivered:
                    sample_delivered = True
                    return [0.05] * 160
                return []
            bridge.get_audio_samples.side_effect = get_samples_mock

            # Retrieve hotkey trigger callbacks from register call
            reg_args = bridge.register_hotkey.call_args[0]
            on_press = reg_args[1]
            on_release = reg_args[2]

            on_press()
            time.sleep(0.01)
            on_release()

            # Wait for text injection event
            start_time = time.time()
            while injected_event_data is None and (time.time() - start_time) < 0.5:
                time.sleep(0.01)

            self.assertIsNotNone(injected_event_data, f"Cycle {i} failed to inject text")
            self.assertEqual(injected_event_data["text"], "stress test utterance")
            self.assertEqual(state_machine.state, AppState.IDLE)
            
            # Clean up subscription callback to avoid scaling overhead
            bus.unsubscribe(TEXT_INJECTED, on_injected)

        # Stop actor threads
        hotkey_actor.stop()
        audio_actor.stop()
        whisper_actor.stop()
        injection_actor.stop()
        overlay_actor.stop()

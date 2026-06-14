import unittest
from unittest.mock import MagicMock, call
from core.events import TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL, HOTKEY_PRESSED, TEXT_INJECTED
from core.state_machine.states import AppState
from actors.injection import InjectionActor

class TestInjectionActor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.bridge = MagicMock()
        self.state_machine = MagicMock()
        self.actor = InjectionActor(self.bus, self.bridge, self.state_machine)

    def test_partial_injection_appends(self):
        # Initial partial
        self.actor.handle_event(TRANSCRIPT_PARTIAL, {"text": "hello"})
        self.bridge.inject_text.assert_called_once_with("hello")
        self.assertEqual(self.actor.injected_text, "hello")
        self.bridge.inject_text.reset_mock()

        # Append next partial
        self.actor.handle_event(TRANSCRIPT_PARTIAL, {"text": "hello world"})
        self.bridge.inject_text.assert_called_once_with(" world")
        self.assertEqual(self.actor.injected_text, "hello world")

    def test_partial_injection_backspaces_on_mismatch(self):
        self.actor.injected_text = "hello count"
        
        # Mismatch correction: count -> brown
        self.actor.handle_event(TRANSCRIPT_PARTIAL, {"text": "hello brown"})
        self.bridge.inject_text.assert_called_once_with("\x08\x08\x08\x08\x08brown")
        self.assertEqual(self.actor.injected_text, "hello brown")

    def test_hotkey_pressed_resets_injected_text(self):
        self.actor.injected_text = "hello"
        self.actor.handle_event(HOTKEY_PRESSED, {})
        self.assertEqual(self.actor.injected_text, "")

    def test_transcription_injection_success(self):
        # Feed partial first
        self.actor.injected_text = "hello"
        
        # Final pass has more text
        self.actor.handle_event(TRANSCRIPT_FINAL, {"text": "hello text"})

        # Check state transitions sequence
        self.state_machine.transition_to.assert_has_calls([
            call(AppState.INJECTING),
            call(AppState.IDLE)
        ])

        # Check native injection call (only injects the delta " text")
        self.bridge.inject_text.assert_called_once_with(" text")
        
        # Check event bus publication
        self.bus.publish.assert_called_once_with(TEXT_INJECTED, {"text": "hello text"})
        self.assertEqual(self.actor.injected_text, "")

    def test_empty_transcription_skips_injection_and_resets(self):
        self.actor.injected_text = "hello"
        self.actor.handle_event(TRANSCRIPT_FINAL, {"text": ""})

        # Delta from "hello" to "" is 5 backspaces
        self.state_machine.transition_to.assert_has_calls([
            call(AppState.INJECTING),
            call(AppState.IDLE)
        ])
        self.bridge.inject_text.assert_called_once_with("\x08\x08\x08\x08\x08")
        self.assertEqual(self.actor.injected_text, "")

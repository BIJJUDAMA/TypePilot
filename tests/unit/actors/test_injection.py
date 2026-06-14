import unittest
from unittest.mock import MagicMock, call
from core.events import TRANSCRIPT_FINAL, TEXT_INJECTED
from core.state_machine.states import AppState
from actors.injection import InjectionActor

class TestInjectionActor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.bridge = MagicMock()
        self.state_machine = MagicMock()
        self.actor = InjectionActor(self.bus, self.bridge, self.state_machine)

    def test_transcription_injection_success(self):
        self.actor.handle_event(TRANSCRIPT_FINAL, {"text": "hello text"})

        # Check state transitions sequence
        self.state_machine.transition_to.assert_has_calls([
            call(AppState.INJECTING),
            call(AppState.IDLE)
        ])

        # Check native injection call
        self.bridge.inject_text.assert_called_once_with("hello text")
        
        # Check event bus publication
        self.bus.publish.assert_called_once_with(TEXT_INJECTED, {"text": "hello text"})

    def test_empty_transcription_skips_injection(self):
        self.actor.handle_event(TRANSCRIPT_FINAL, {"text": ""})

        self.bridge.inject_text.assert_not_called()
        self.state_machine.transition_to.assert_called_once_with(AppState.IDLE)
        self.bus.publish.assert_not_called()

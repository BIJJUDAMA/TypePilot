import unittest
from unittest.mock import MagicMock
from core.events import HOTKEY_PRESSED, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL, TEXT_INJECTED, ERROR
from actors.overlay import OverlayActor

class TestOverlayActor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.window = MagicMock()
        self.actor = OverlayActor(self.bus, self.window)

    def test_hotkey_pressed(self):
        self.actor.handle_event(HOTKEY_PRESSED, {})
        self.window.update_text_signal.emit.assert_called_once_with("")
        self.window.update_status_signal.emit.assert_called_once_with("Listening...")
        self.window.show_signal.emit.assert_called_once()

    def test_transcript_partial(self):
        self.actor.handle_event(TRANSCRIPT_PARTIAL, {"text": "hello partial"})
        self.window.update_text_signal.emit.assert_called_once_with("hello partial")

    def test_transcript_final(self):
        self.actor.handle_event(TRANSCRIPT_FINAL, {"text": "hello final"})
        self.window.update_text_signal.emit.assert_called_once_with("hello final")
        self.window.update_status_signal.emit.assert_called_once_with("Processing...")

    def test_text_injected(self):
        self.actor.handle_event(TEXT_INJECTED, {})
        self.window.hide_signal.emit.assert_called_once()

    def test_error_handling(self):
        self.actor.handle_event(ERROR, {"message": "Microphone not found"})
        self.window.update_status_signal.emit.assert_called_once_with("Error")
        self.window.update_text_signal.emit.assert_called_once_with("Microphone not found")
        self.window.show_signal.emit.assert_called_once()

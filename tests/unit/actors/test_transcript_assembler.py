import unittest
from unittest.mock import MagicMock, patch
from core.events import HOTKEY_PRESSED, HOTKEY_RELEASED, TRANSCRIPT_SEGMENT, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL
from actors.transcript_assembler import TranscriptAssemblerActor

class TestTranscriptAssemblerActor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.actor = TranscriptAssemblerActor(self.bus)

    def test_segment_stitching_and_finalization(self):
        # Reset state
        self.actor.handle_event(HOTKEY_PRESSED, {})
        
        # Segment 1
        self.actor.handle_event(TRANSCRIPT_SEGMENT, {
            "text": "hello everyone welcome",
            "is_final": False
        })
        self.bus.publish.assert_called_with(TRANSCRIPT_PARTIAL, {"text": "hello everyone welcome"})
        
        # Segment 2 (overlapping)
        self.actor.handle_event(TRANSCRIPT_SEGMENT, {
            "text": "everyone welcome to",
            "is_final": False
        })
        self.bus.publish.assert_called_with(TRANSCRIPT_PARTIAL, {"text": "hello everyone welcome to"})
        
        # Trigger hotkey release to enter waiting_for_final state
        self.actor.handle_event(HOTKEY_RELEASED, {})
        
        # Segment 3 (final segment)
        self.bus.publish.reset_mock()
        self.actor.handle_event(TRANSCRIPT_SEGMENT, {
            "text": "welcome to todays meeting",
            "is_final": True
        })
        
        # Should publish final transcript
        self.bus.publish.assert_any_call(TRANSCRIPT_PARTIAL, {"text": "hello everyone welcome to todays meeting"})
        self.bus.publish.assert_any_call(TRANSCRIPT_FINAL, {"text": "hello everyone welcome to todays meeting"})

    @patch('threading.Timer')
    def test_safety_timer_fallback(self, mock_timer):
        # Trigger the safety timer callback immediately
        timer_callbacks = []
        def mock_timer_init(interval, function, *args, **kwargs):
            timer_callbacks.append(function)
            mock_t = MagicMock()
            mock_t.start = lambda: None
            return mock_t
        mock_timer.side_effect = mock_timer_init

        self.actor.handle_event(HOTKEY_PRESSED, {})
        self.actor.handle_event(TRANSCRIPT_SEGMENT, {
            "text": "hello everyone",
            "is_final": False
        })
        
        # Release hotkey without final segment arriving
        self.actor.handle_event(HOTKEY_RELEASED, {})
        self.assertTrue(self.actor.is_waiting_for_final)
        
        # Trigger safety timeout callback manually
        self.assertEqual(len(timer_callbacks), 1)
        timer_callbacks[0]()
        
        # Should have force finalized
        self.bus.publish.assert_called_with(TRANSCRIPT_FINAL, {"text": "hello everyone"})
        self.assertFalse(self.actor.is_waiting_for_final)

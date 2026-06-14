import unittest
from unittest.mock import MagicMock
from core.events import HOTKEY_PRESSED, HOTKEY_RELEASED
from core.state_machine.states import AppState
from actors.hotkey import HotkeyActor

class TestHotkeyActor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.bridge = MagicMock()
        self.state_machine = MagicMock()
        self.actor = HotkeyActor(self.bus, self.bridge, self.state_machine)

    def test_start_registers_callbacks(self):
        self.actor.start()
        self.bridge.register_hotkey.assert_called_once()
        args = self.bridge.register_hotkey.call_args[0]
        self.assertEqual(args[0], 0x20)
        self.assertTrue(callable(args[1]))
        self.assertTrue(callable(args[2]))
        self.actor.stop()

    def test_callbacks_publish_events(self):
        self.actor.start()
        args = self.bridge.register_hotkey.call_args[0]
        press_callback = args[1]
        release_callback = args[2]

        self.state_machine.state = AppState.IDLE
        press_callback()
        self.state_machine.state = AppState.LISTENING
        release_callback()

        self.bus.publish.assert_any_call(HOTKEY_PRESSED, self.bus.publish.call_args_list[0][0][1])
        self.bus.publish.assert_any_call(HOTKEY_RELEASED, self.bus.publish.call_args_list[1][0][1])
        self.actor.stop()

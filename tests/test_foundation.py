from core.events import (
    HOTKEY_PRESSED, HOTKEY_RELEASED, AUDIO_CHUNK, 
    TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL, ERROR
)
from core.state_machine.states import AppState

def test_events_defined():
    assert HOTKEY_PRESSED == "HOTKEY_PRESSED"
    assert HOTKEY_RELEASED == "HOTKEY_RELEASED"
    assert AUDIO_CHUNK == "AUDIO_CHUNK"
    assert TRANSCRIPT_PARTIAL == "TRANSCRIPT_PARTIAL"
    assert TRANSCRIPT_FINAL == "TRANSCRIPT_FINAL"
    assert ERROR == "ERROR"

def test_app_states_defined():
    assert AppState.IDLE.name == "IDLE"
    assert AppState.LISTENING.name == "LISTENING"
    assert AppState.PROCESSING.name == "PROCESSING"
    assert AppState.INJECTING.name == "INJECTING"
    assert AppState.ERROR.name == "ERROR"

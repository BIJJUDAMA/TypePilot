import pytest
from core.platform import PlatformBridge

def test_platform_bridge_methods():
    """Verify that the PlatformBridge methods can be called without error (stubs)."""
    bridge = PlatformBridge()
    
    # Test register_hotkey
    def dummy_callback():
        pass
    bridge.register_hotkey(0x20, dummy_callback, dummy_callback)
    
    # Test audio capture methods
    bridge.start_audio_capture()
    bridge.stop_audio_capture()
    
    # Test inject_text
    bridge.inject_text("Hello World")

from typing import Callable
from core.logging import get_logger

class PlatformBridge:
    """
    Wrapper for the Rust PyO3 bridge.
    
    NOTE: This is currently a stub implementation. In production, this will 
    interface with the 'typepilot_native' Rust module.
    """
    def __init__(self):
        self.logger = get_logger("PlatformBridge")
        # In a real setup, this would import the compiled Rust module
        # self.bridge = importlib.import_module("typepilot_native")

    def register_hotkey(self, key_code: int, callback: Callable[[], None]) -> None:
        """
        Registers a system-wide hotkey.
        """
        self.logger.info(f"Registered hotkey: {key_code}")

    def start_audio_capture(self) -> None:
        """
        Signals the native layer to begin audio capture.
        """
        self.logger.info("Audio capture started")

    def stop_audio_capture(self) -> None:
        """
        Signals the native layer to stop audio capture.
        """
        self.logger.info("Audio capture stopped")

    def inject_text(self, text: str) -> None:
        """
        Injects text into the currently focused window.
        """
        self.logger.info(f"Injected text: {text}")

from typing import Callable, List
from core.logging import get_logger

class PlatformBridge:
    """Wrapper for the native Rust extension module."""
    def __init__(self):
        self.logger = get_logger("PlatformBridge")
        self.native = None
        try:
            import typepilot_native
            self.native = typepilot_native
            self.logger.info("Successfully loaded typepilot_native extension")
        except ImportError:
            self.logger.warning("typepilot_native extension not found. Using stubs.")

    def register_hotkey(self, key_code: int, callback_press: Callable[[], None], callback_release: Callable[[], None]) -> None:
        """Registers system-wide hotkey callbacks."""
        if self.native:
            self.native.register_hotkey(callback_press, callback_release)
        else:
            self.logger.info(f"[Stub] Register hotkey {key_code}")

    def unregister_hotkey(self) -> None:
        """Unregisters system-wide hotkey hook."""
        if self.native:
            self.native.unregister_hotkey()
        else:
            self.logger.info("[Stub] Unregister hotkey")

    def start_audio_capture(self) -> None:
        """Starts audio recording stream."""
        if self.native:
            self.native.start_audio_capture()
        else:
            self.logger.info("[Stub] Start audio capture")

    def stop_audio_capture(self) -> None:
        """Stops audio recording stream."""
        if self.native:
            self.native.stop_audio_capture()
        else:
            self.logger.info("[Stub] Stop audio capture")

    def get_audio_samples(self) -> List[float]:
        """Retrieves captured float32 audio samples."""
        if self.native:
            return self.native.get_audio_samples()
        return []

    def inject_text(self, text: str) -> None:
        """Injects text into focused window."""
        if self.native:
            self.native.inject_text(text)
        else:
            self.logger.info(f"[Stub] Inject text: {text}")

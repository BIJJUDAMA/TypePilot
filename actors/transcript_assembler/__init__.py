import threading
from core.actor import Actor
from core.events import HOTKEY_PRESSED, HOTKEY_RELEASED, TRANSCRIPT_SEGMENT, TRANSCRIPT_PARTIAL, TRANSCRIPT_FINAL

def merge_word_lists(words1, words2):
    if not words1:
        return words2
    if not words2:
        return words1

    # Check if words2 is already contained as a sublist in words1
    # looking at the end of words1 (up to len(words2)*2)
    lookback = min(len(words1), len(words2) + 5)
    main_slice = words1[-lookback:]
    for i in range(len(main_slice) - len(words2) + 1):
        if main_slice[i:i+len(words2)] == words2:
            return words1

    # Try exact suffix-prefix match
    max_overlap = min(len(words1), len(words2))
    for L in range(max_overlap, 0, -1):
        if words1[-L:] == words2[:L]:
            return words1 + words2[L:]

    # Try fuzzy suffix-prefix match (score >= 0.75, L >= 2)
    best_L = 0
    best_score = 0.0
    for L in range(max_overlap, 1, -1):
        w1 = words1[-L:]
        w2 = words2[:L]
        matches = sum(1 for a, b in zip(w1, w2) if a == b)
        score = matches / L
        if score >= 0.75 and score > best_score:
            best_score = score
            best_L = L

    if best_L > 0:
        return words1 + words2[best_L:]

    return words1 + words2


class TranscriptAssemblerActor(Actor):
    """Stitches overlapping partial transcripts into a continuous growing text."""
    def __init__(self, event_bus):
        super().__init__(event_bus)
        self.assembled_words = []
        self.is_active = False
        self.is_waiting_for_final = False
        self.safety_timer = None
        self.lock = threading.Lock()

        self.subscribe(HOTKEY_PRESSED)
        self.subscribe(HOTKEY_RELEASED)
        self.subscribe(TRANSCRIPT_SEGMENT)

    def handle_event(self, event_type, data):
        if event_type == HOTKEY_PRESSED:
            self._handle_hotkey_pressed()
        elif event_type == TRANSCRIPT_SEGMENT:
            self._handle_transcript_segment(data)
        elif event_type == HOTKEY_RELEASED:
            self._handle_hotkey_released()

    def _handle_hotkey_pressed(self):
        with self.lock:
            self._cancel_safety_timer()
            self.assembled_words = []
            self.is_active = True
            self.is_waiting_for_final = False
            self.logger.info("Transcript Assembler reset for new dictation")

    def _handle_transcript_segment(self, data):
        with self.lock:
            if not self.is_active and not self.is_waiting_for_final:
                self.logger.debug("Ignoring stray transcript segment received outside active/waiting state")
                return

            text = data.get("text", "").strip()
            is_final = data.get("is_final", False)
            
            if text:
                segment_words = text.split()
                self.assembled_words = merge_word_lists(self.assembled_words, segment_words)
            
            assembled_text = " ".join(self.assembled_words)
            
            # Publish partial transcript
            if assembled_text:
                self.event_bus.publish(TRANSCRIPT_PARTIAL, {"text": assembled_text})
                
            if is_final:
                if self.is_waiting_for_final:
                    self._finalize(assembled_text)
                else:
                    self.logger.warning("Received final segment but was not waiting for final. Resetting.")
                    self.assembled_words = []

    def _handle_hotkey_released(self):
        with self.lock:
            if not self.is_active:
                return
            self.is_active = False
            # When hotkey is released, we start waiting for the final segment to arrive
            self.is_waiting_for_final = True
            # Setup a safety timer for 5.0 seconds in case the final segment is missed
            self._cancel_safety_timer()
            self.safety_timer = threading.Timer(5.0, self._on_safety_timeout)
            self.safety_timer.daemon = True
            self.safety_timer.start()
            self.logger.info("Transcript Assembler waiting for final segment with safety timer")

    def _on_safety_timeout(self):
        with self.lock:
            if self.is_waiting_for_final:
                self.logger.warning("Safety timer expired waiting for final segment. Force finalizing.")
                assembled_text = " ".join(self.assembled_words)
                self._finalize(assembled_text)

    def _finalize(self, text):
        self._cancel_safety_timer()
        self.is_waiting_for_final = False
        self.is_active = False
        self.logger.info(f"Publishing final transcript: '{text}'")
        self.event_bus.publish(TRANSCRIPT_FINAL, {"text": text})
        self.assembled_words = []

    def _cancel_safety_timer(self):
        if self.safety_timer:
            self.safety_timer.cancel()
            self.safety_timer = None

    def stop(self):
        with self.lock:
            self._cancel_safety_timer()
        super().stop()

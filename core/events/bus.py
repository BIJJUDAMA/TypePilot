import threading
from collections import defaultdict
from typing import Callable, Any, Dict
from core.logging import get_logger

logger = get_logger("core.events.bus")

class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    if not self._subscribers[event_type]:
                        del self._subscribers[event_type]
                except ValueError:
                    logger.warning(f"Attempted to unsubscribe a callback that was not registered for event {event_type}")

    def publish(self, event_type: str, data: Dict[str, Any] = None):
        if data is None:
            data = {}
        
        # Copy the subscribers list while holding the lock to minimize contention during execution
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))
            
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in subscriber callback for event {event_type}: {e}")

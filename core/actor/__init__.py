import threading
import queue
from abc import ABC, abstractmethod
from core.logging import get_logger

class Actor(ABC):
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.queue = queue.Queue()
        self._running_event = threading.Event()
        self._subscriptions = {}  # event_type -> callback
        self._lock = threading.Lock()
        self.thread = None
        self.logger = get_logger(self.__class__.__name__)

    def start(self):
        with self._lock:
            if self._running_event.is_set():
                self.logger.warning("Already running")
                return
            
            self._running_event.set()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            self.logger.info("Started")

    def stop(self):
        with self._lock:
            if not self._running_event.is_set():
                return

            self._running_event.clear()
            self.queue.put(None) # Sentinel to break the loop
            
            # Unsubscribe from all events
            for event_type, callback in list(self._subscriptions.items()):
                self.event_bus.unsubscribe(event_type, callback)
            self._subscriptions.clear()

            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
            self.logger.info("Stopped")

    def _run_loop(self):
        while self._running_event.is_set():
            try:
                item = self.queue.get(timeout=0.1)
                if item is None:
                    break
                event_type, data = item
                self.handle_event(event_type, data)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in loop: {e}")

    @abstractmethod
    def handle_event(self, event_type, data):
        """Handle incoming events. Must be implemented by subclasses."""
        pass

    def _enqueue(self, event_type, data):
        self.queue.put((event_type, data))

    def subscribe(self, event_type):
        """Subscribe to an event type and enqueue it when published."""
        with self._lock:
            if event_type in self._subscriptions:
                return

            def callback(data):
                self._enqueue(event_type, data)
            
            self._subscriptions[event_type] = callback
            self.event_bus.subscribe(event_type, callback)

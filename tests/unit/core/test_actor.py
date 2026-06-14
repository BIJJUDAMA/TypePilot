import threading
import time
import pytest
from core.actor import Actor
from core.events.bus import EventBus

class MockActor(Actor):
    def __init__(self, event_bus):
        super().__init__(event_bus)
        self.received = []
        self.handle_count = 0
        
    def handle_event(self, event_type, data):
        self.received.append((event_type, data))
        self.handle_count += 1

def test_actor_lifecycle():
    bus = EventBus()
    actor = MockActor(bus)
    
    # Subscribe to an event
    actor.subscribe("MOCK_EVENT")
    
    actor.start()
    
    bus.publish("MOCK_EVENT", {"val": 1})
    
    # Wait for the actor to process the event from its queue
    timeout = 1.0
    start_time = time.time()
    while len(actor.received) == 0 and (time.time() - start_time) < timeout:
        time.sleep(0.01)
    
    assert len(actor.received) == 1
    assert actor.received[0] == ("MOCK_EVENT", {"val": 1})
    
    actor.stop()
    assert not actor._running_event.is_set()

def test_actor_start_guard(caplog):
    bus = EventBus()
    actor = MockActor(bus)
    
    actor.start()
    with caplog.at_level("WARNING"):
        actor.start() # Should trigger warning
    
    assert "Already running" in caplog.text
    actor.stop()

def test_actor_unsubscribe_on_stop():
    bus = EventBus()
    actor = MockActor(bus)
    
    actor.subscribe("MOCK_EVENT")
    actor.start()
    actor.stop()
    
    # After stopping, publishing to MOCK_EVENT should NOT result in it being enqueued
    bus.publish("MOCK_EVENT", {"val": 2})
    
    # The queue should be empty (except maybe the None sentinel if we didn't join yet, but stop() joins)
    assert actor.queue.empty()

def test_actor_concurrent_start_stop():
    bus = EventBus()
    actor = MockActor(bus)
    
    def worker():
        for _ in range(50):
            actor.start()
            time.sleep(0.001)
            actor.stop()
            time.sleep(0.001)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # After all that, the actor should be stopped and stable
    assert not actor._running_event.is_set()
    if actor.thread:
        assert not actor.thread.is_alive()

def test_actor_concurrent_subscribe():
    bus = EventBus()
    actor = MockActor(bus)
    
    def worker(i):
        actor.subscribe(f"EVENT_{i}")

    threads = [threading.Thread(target=worker, args=(i % 5,)) for i in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should have exactly 5 subscriptions
    assert len(actor._subscriptions) == 5

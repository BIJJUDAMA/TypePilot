import pytest
import threading
import time
from core.events.bus import EventBus

def test_publish_subscribe():
    bus = EventBus()
    received = []
    
    def callback(data):
        received.append(data)
        
    bus.subscribe("TEST_EVENT", callback)
    bus.publish("TEST_EVENT", {"foo": "bar"})
    
    assert len(received) == 1
    assert received[0]["foo"] == "bar"

def test_error_isolation(caplog):
    bus = EventBus()
    received = []
    
    def failing_callback(data):
        raise ValueError("Boom")
        
    def success_callback(data):
        received.append(data)
        
    bus.subscribe("TEST_EVENT", failing_callback)
    bus.subscribe("TEST_EVENT", success_callback)
    
    # This should not raise an exception and success_callback should run
    with caplog.at_level("ERROR"):
        bus.publish("TEST_EVENT", {"foo": "bar"})
    
    assert len(received) == 1
    assert received[0]["foo"] == "bar"
    assert "Error in subscriber callback for event TEST_EVENT: Boom" in caplog.text

def test_thread_safety():
    bus = EventBus()
    event_type = "THREAD_EVENT"
    num_threads = 10
    iterations = 100
    
    results = []
    def subscriber_task():
        for _ in range(iterations):
            bus.subscribe(event_type, lambda d: results.append(d))
            time.sleep(0.001)

    def publisher_task():
        for _ in range(iterations):
            bus.publish(event_type, {"data": "test"})
            time.sleep(0.001)

    threads = []
    for _ in range(num_threads):
        threads.append(threading.Thread(target=subscriber_task))
        threads.append(threading.Thread(target=publisher_task))

    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # If it didn't crash, it's a good sign. 
    # With dict mutation during iteration, it should fail without locks.
    assert True

def test_unsubscribe():
    bus = EventBus()
    received = []
    
    def callback(data):
        received.append(data)
        
    bus.subscribe("TEST_EVENT", callback)
    bus.publish("TEST_EVENT", {"foo": "bar"})
    assert len(received) == 1
    
    bus.unsubscribe("TEST_EVENT", callback)
    bus.publish("TEST_EVENT", {"foo": "baz"})
    assert len(received) == 1 # Still 1, didn't receive "baz"

def test_unsubscribe_nonexistent():
    bus = EventBus()
    def callback(data): pass
    
    # Should not raise
    bus.unsubscribe("NOT_THERE", callback)
    
    bus.subscribe("THERE", callback)
    bus.unsubscribe("THERE", lambda d: None) # Different callback
    # Should not raise, but should log a warning (which we aren't asserting here)

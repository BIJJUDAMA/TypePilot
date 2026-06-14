import pytest
import threading
import time
from core.state_machine import AppStateMachine
from core.state_machine.states import AppState

def test_state_transitions():
    sm = AppStateMachine()
    assert sm.state == AppState.IDLE
    
    sm.transition_to(AppState.LISTENING)
    assert sm.state == AppState.LISTENING
    
    with pytest.raises(ValueError):
        sm.transition_to(AppState.INJECTING) # Invalid Idle -> Injecting

def test_concurrent_transitions():
    sm = AppStateMachine()
    results = []
    
    def attempt_transition(target_state):
        try:
            sm.transition_to(target_state)
            results.append(True)
        except ValueError:
            results.append(False)

    # From IDLE, both try to transition to LISTENING
    # Only one should succeed if they were actually competing for the same state change
    # but here they are just two threads calling the same valid transition.
    # The lock ensures that the check and update are atomic.
    
    t1 = threading.Thread(target=attempt_transition, args=(AppState.LISTENING,))
    t2 = threading.Thread(target=attempt_transition, args=(AppState.LISTENING,))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    # One should succeed (transitioning IDLE -> LISTENING)
    # The other should fail (transitioning LISTENING -> LISTENING is not in valid transitions)
    assert results.count(True) == 1
    assert results.count(False) == 1
    assert sm.state == AppState.LISTENING

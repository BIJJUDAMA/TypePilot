import threading
from core.state_machine.states import AppState
from core.logging import get_logger

class AppStateMachine:
    def __init__(self):
        self.state = AppState.IDLE
        self.logger = get_logger("AppStateMachine")
        self._lock = threading.Lock()
        self._valid_transitions = {
            AppState.IDLE: [AppState.LISTENING, AppState.ERROR],
            AppState.LISTENING: [AppState.PROCESSING, AppState.ERROR],
            AppState.PROCESSING: [AppState.INJECTING, AppState.IDLE, AppState.ERROR],
            AppState.INJECTING: [AppState.IDLE, AppState.ERROR],
            AppState.ERROR: [AppState.IDLE]
        }

    def transition_to(self, next_state: AppState):
        with self._lock:
            if next_state not in self._valid_transitions.get(self.state, []):
                msg = f"Invalid transition: {self.state} -> {next_state}"
                self.logger.error(msg)
                raise ValueError(msg)
            
            self.logger.info(f"Transition: {self.state} -> {next_state}")
            self.state = next_state

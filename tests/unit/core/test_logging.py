import logging
import sys
from core.logging import get_logger

def test_get_logger():
    logger = get_logger("TestLogger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "TestLogger"
    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.handlers[0].stream == sys.stdout

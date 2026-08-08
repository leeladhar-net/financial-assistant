import logging
import sys
from collections import deque
from app.core.config import settings

# Global thread-safe/in-memory log buffer for /debug endpoint
LOG_BUFFER = deque(maxlen=100)

class MemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            LOG_BUFFER.append(msg)
        except Exception:
            self.handleError(record)

def setup_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    mem_handler = MemoryLogHandler()
    mem_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicate logging
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        
    root_logger.addHandler(handler)
    root_logger.addHandler(mem_handler)

    # Silence noisy external libraries if needed
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("financial_assistant")

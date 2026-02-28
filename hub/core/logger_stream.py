import logging
import asyncio
import sys
from collections import deque

class MemoryStreamHandler(logging.Handler):
    def __init__(self, capacity=1000):
        super().__init__()
        self.capacity = capacity
        self.logs = deque(maxlen=capacity)
        self.listeners = set()
        # Basic matching formatter
        self.setFormatter(logging.Formatter('%(levelname)s:\t  %(message)s'))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.logs.append(msg)
            
            # Print to the real stdout so it goes to hub.log
            try:
                print(msg, file=sys.__stdout__, flush=True)
            except Exception:
                # Fallback for Windows consoles with limited encodings (e.g. cp1252).
                try:
                    if hasattr(sys.__stdout__, "buffer"):
                        sys.__stdout__.buffer.write((msg + "\n").encode("utf-8", "replace"))
                        sys.__stdout__.buffer.flush()
                except Exception:
                    pass

            # Notify all connected websockets
            for queue in list(self.listeners):
                try:
                    queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass
        except Exception:
            self.handleError(record)

    def add_listener(self, queue: asyncio.Queue):
        self.listeners.add(queue)
        
    def remove_listener(self, queue: asyncio.Queue):
        self.listeners.discard(queue)

stream_handler = MemoryStreamHandler()

class PrintToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.buffer = ""

    def write(self, message):
        if message == '\n':
            return
        # If it ends with \n, log it immediately
        if message.endswith('\n'):
            self.logger.log(self.level, self.buffer + message.rstrip())
            self.buffer = ""
        else:
            self.buffer += message

    def flush(self):
        pass

    def isatty(self):
        """Required by libraries (e.g. transformers) that check stdout.isatty() for colored output."""
        return False

def setup_log_capture():
    # Attach to root and uvicorn loggers
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if stream_handler not in root.handlers:
        root.addHandler(stream_handler)
    
    # Uvicorn specific
    for name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        l = logging.getLogger(name)
        if stream_handler not in l.handlers:
            l.addHandler(stream_handler)

    # Capture print() statements
    print_logger = logging.getLogger("stdout")
    if stream_handler not in print_logger.handlers:
        print_logger.addHandler(stream_handler)
        sys.stdout = PrintToLogger(print_logger, logging.INFO)
        sys.stderr = PrintToLogger(print_logger, logging.ERROR)

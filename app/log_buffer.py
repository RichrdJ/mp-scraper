import logging
from collections import deque
from threading import Lock

_buffer: deque = deque(maxlen=500)
_lock = Lock()


class _BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        with _lock:
            _buffer.append({
                'time': record.asctime if hasattr(record, 'asctime') else '',
                'level': record.levelname,
                'msg': record.getMessage(),
                'name': record.name,
            })


_handler = _BufferHandler()
_handler.setFormatter(logging.Formatter('%(asctime)s'))


def setup() -> None:
    """Attach the memory handler to the root logger."""
    logging.getLogger().addHandler(_handler)


def get_recent(n: int = 150) -> list[dict]:
    with _lock:
        logs = list(_buffer)
    return logs[-n:]

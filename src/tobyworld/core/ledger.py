from collections import deque
from threading import Lock
from time import time
from typing import Any, Deque, Dict, List

class Ledger:
    def __init__(self, maxlen: int = 1000) -> None:
        self._q: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = Lock()

    # New: the method MirrorCore expects
    def add(self, kind: str, data: Dict[str, Any] | None = None) -> None:
        rec = {"t": time(), "kind": kind, "data": data or {}}
        with self._lock:
            self._q.append(rec)

    # Back-compat alias if other code calls .log(...)
    def log(self, *args, **kwargs) -> None:
        return self.add(*args, **kwargs)

    def recent(self, n: int = 5) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._q)[-n:]

from collections import deque
from time import time

class Ledger:
    def __init__(self, maxlen: int = 2000):
        self._q = deque(maxlen=maxlen)

    def log(self, kind: str, data: dict | None = None):
        self._q.append({"t": time(), "kind": kind, "data": data or {}})

    def recent(self, n: int = 10):
        return list(self._q)[-n:]

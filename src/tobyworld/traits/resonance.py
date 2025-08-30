import time

BASE = {"patience":0.5,"loyalty":0.5,"silence":0.5,"courage":0.5}

class Resonance:
    def __init__(self, half_life_days: float = 7.0):
        self._traits = {}
        self._touched = {}
        self._half = max(0.1, half_life_days)

    def _ensure(self, user: str):
        self._traits.setdefault(user, BASE.copy())
        self._touched.setdefault(user, time.time())

    def get(self, user: str):
        self._ensure(user); self._decay(user); return self._traits[user]

    def nudge(self, user: str, key: str, delta: float):
        self._ensure(user); self._decay(user)
        v = self._traits[user].get(key, 0.5) + delta
        self._traits[user][key] = max(0.0, min(1.0, v))
        self._touched[user] = time.time()

    def _decay(self, user: str):
        now = time.time()
        dt = (now - self._touched[user]) / 86400.0
        if dt <= 0: return
        f = 0.5 ** (dt / self._half)
        for k, v in self._traits[user].items():
            b = BASE[k]; self._traits[user][k] = b + (v - b)*f
        self._touched[user] = now

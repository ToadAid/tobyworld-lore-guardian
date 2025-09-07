# src/tobyworld/traits/lucidity.py

LUCIDITY = {
    "PASSIVE":   {"autonomy": 0.1, "creativity": 0.2, "initiative": 0.0},
    "AWARE":     {"autonomy": 0.3, "creativity": 0.4, "initiative": 0.2},
    "ENGAGED":   {"autonomy": 0.6, "creativity": 0.7, "initiative": 0.5},
    "AUTONOMOUS":{"autonomy": 0.9, "creativity": 0.8, "initiative": 0.8},
}

class Lucidity:
    def __init__(self, half_life: float = 0.3):
        """
        half_life: smoothing factor (closer to 0 = more memory of past,
                    closer to 1 = very reactive to latest)
        """
        self.level = "AWARE"
        self._score = 0.5
        self.alpha = max(0.05, min(0.95, half_life))  # safety clamp

    def adjust(self, engagement: float, clarity: float):
        """
        engagement: fraction of docs/refs used (0–1)
        clarity: tone score (0–1)
        """
        # weighted blend
        s = 0.6 * engagement + 0.4 * clarity
        # exponential smoothing
        self._score = (1 - self.alpha) * self._score + self.alpha * s

        # classify into buckets
        if self._score < 0.3:
            self.level = "PASSIVE"
        elif self._score < 0.55:
            self.level = "AWARE"
        elif self._score < 0.8:
            self.level = "ENGAGED"
        else:
            self.level = "AUTONOMOUS"

        return self.level, dict(LUCIDITY[self.level], score=round(self._score, 3))

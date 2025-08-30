LUCIDITY = {
    "PASSIVE":{"autonomy":0.1,"creativity":0.2,"initiative":0.0},
    "AWARE":{"autonomy":0.3,"creativity":0.4,"initiative":0.2},
    "ENGAGED":{"autonomy":0.6,"creativity":0.7,"initiative":0.5},
    "AUTONOMOUS":{"autonomy":0.9,"creativity":0.8,"initiative":0.8},
}

class Lucidity:
    def __init__(self):
        self.level = "AWARE"
        self._score = 0.5

    def adjust(self, engagement: float, clarity: float):
        s = 0.6*engagement + 0.4*clarity
        self._score = 0.7*self._score + 0.3*s
        self.level = ("PASSIVE" if self._score < 0.3 else
                      "AWARE" if self._score < 0.55 else
                      "ENGAGED" if self._score < 0.8 else "AUTONOMOUS")
        return self.level, LUCIDITY[self.level]

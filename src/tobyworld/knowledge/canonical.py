class Canonical:
    def __init__(self):
        self._facts = {"TOBY_total_supply": "420,000,000,000,000"}

    def all(self):
        return dict(self._facts)

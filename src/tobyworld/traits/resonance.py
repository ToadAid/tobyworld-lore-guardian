# src/tobyworld/traits/resonance.py
from __future__ import annotations

import time
import math
import re
from typing import Dict, Any, List, Optional

# =========================
# (A) User-trait resonance
# =========================
BASE = {"patience": 0.5, "loyalty": 0.5, "silence": 0.5, "courage": 0.5}

class Resonance:
    """
    Per-user trait resonance with half-life decay back to BASE.
    Keep this exactly as in V2 so existing callers don't break.
    """
    def __init__(self, half_life_days: float = 7.0):
        self._traits: Dict[str, Dict[str, float]] = {}
        self._touched: Dict[str, float] = {}
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
            b = BASE[k]; self._traits[user][k] = b + (v - b) * f
        self._touched[user] = now


# ==========================================
# (B) RAG doc scoring resonance (half-life)
# ==========================================
# Minimal DocBlob protocol (avoid imports/cycles)
class _DocLike:
    doc_id: str
    text: str
    meta: Dict[str, Any]
    score: float

class Rescorer:
    """Interface: re-rank docs in-place and return them."""
    def rescore(self, query: str, docs: List[_DocLike]) -> List[_DocLike]:
        return docs

class HalfLifeRescorer(Rescorer):
    """
    Score' = Score * decay(age_days, half_life_days) * (1 + α * topic_boost)

    - decay = 0.5 ** (age_days / half_life_days)
    - topic_boost comes from LearningStore topic counters (log-normalized 0..1),
      if a learning_store with .top_topics(n) is provided.
    """
    def __init__(
        self,
        learning_store: Optional[object] = None,   # expects .top_topics(n)->[{topic,count,last_ts}]
        half_life_days: float = 14.0,
        alpha: float = 0.25,
        ts_key: str = "timestamp",
    ):
        self.learning = learning_store
        self.half = max(1e-6, float(half_life_days))
        self.alpha = float(alpha)
        self.ts_key = ts_key
        self._token_rx = re.compile(r"[a-z0-9]{3,}")

        # tiny stoplist to avoid bland words in topic boost
        self._stop = {
            "what", "who", "how", "the", "and", "for", "you", "are",
            "tobyworld", "about", "with", "from"
        }

    def _age_days(self, meta: Dict[str, Any]) -> float:
        ts = meta.get(self.ts_key, 0.0)
        if not isinstance(ts, (int, float)):
            return 1e9
        return max(0.0, (time.time() - float(ts)) / 86400.0)

    def _decay(self, age_days: float) -> float:
        return 0.5 ** (age_days / self.half)

    def _topic_boost(self, query: str) -> float:
        if not self.learning:
            return 0.0
        tokens = [t for t in self._token_rx.findall((query or "").lower()) if t not in self._stop]
        if not tokens:
            return 0.0
        stats = self.learning.top_topics(n=64)
        counts = {row["topic"]: int(row.get("count", 0)) for row in stats}
        s = sum(counts.get(t, 0) for t in tokens)
        if s <= 0:
            return 0.0
        # log normalization; ~1.0 around ~20 recent hits
        return min(1.0, math.log1p(s) / math.log1p(20.0))

    def rescore(self, query: str, docs: List[_DocLike]) -> List[_DocLike]:
        tb = self._topic_boost(query)
        for d in docs:
            age = self._age_days(getattr(d, "meta", {}) or {})
            decay = self._decay(age)
            d.score = float(d.score) * decay * (1.0 + self.alpha * tb)
        docs.sort(key=lambda x: x.score, reverse=True)
        return docs

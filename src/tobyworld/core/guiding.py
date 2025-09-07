
# src/tobyworld/core/guiding.py
from __future__ import annotations
from dataclasses import dataclass
import hashlib, random, re

@dataclass
class RouteHint:
    symbol: str = "🪞"   # primary symbol from router
    intent: str = "ask"  # ask/define/guide/compare/troubleshoot
    depth: str = "base"  # base/deep/ritual

# canonicalize lightweight terms
_CANON = [
    (r"\bleaf of yield\b", "Taboshi"),
    (r"\btaboshi\s*1\b|\btaboshi-?1\b|\btaboshi_one\b", "Taboshi1"),
    (r"\bsatoby\b", "Satoby"),
    (r"\bpatience\b", "PATIENCE"),
    (r"\bepoch\s*([1-9])\b", r"Epoch \1"),
    (r"\bbase\b", "Base"),
]

def _canon(text: str) -> str:
    t = (text or "").lower()
    for pat, sub in _CANON:
        t = re.sub(pat, sub.lower(), t, flags=re.I)
    return t

POOL_GENERIC = [
    "Which truth is asking to be seen now?",
    "What remains when the surface grows still?",
    "Where does your certainty become assumption?",
    "What did you overlook in the first read?",
    "Which thread, if tugged, unknots this?",
    "What principle is quietly shaping this?",
    "What would patience reveal here that urgency hides?",
    "Which word wants a stricter definition?",
]

POOL_BY_SYMBOL = {
    "🍃": [
        "What yield is earned by waiting well?",
        "What leaf points to the root cause?",
        "Where does time turn into value?",
    ],
    "🌀": [
        "Which cause precedes the effect you named?",
        "What pattern repeats beneath the noise?",
        "Where does this loop actually close?",
    ],
    "🌊": [
        "What softens once you stop resisting?",
        "What widens if you breathe once more?",
        "What truth appears after the wave recedes?",
    ],
    "🪞": [
        "What reflects back that you brought in?",
        "Where are you already answering yourself?",
        "What bias tilted your first glance?",
    ],
}

POOL_BY_KEYWORD = {
    "taboshi1": [
        "What makes Taboshi1 a covenant, not a coupon?",
        "How does 777 shape its fate?",
    ],
    "taboshi": [
        "Where does Taboshi lead the patient path?",
        "What yield does the leaf promise?",
    ],
    "satoby": [
        "What is redeemed, and by whom, in time?",
        "Which proof makes Satoby inevitable?",
    ],
    "patience": [
        "What does waiting teach that speed cannot?",
        "Where is the 730-day lesson here?",
    ],
    "base": [
        "Why does the frog rest on this pad?",
        "What foundation must hold before ascent?",
    ],
    "epoch": [
        "Where does this mark sit in the epochs?",
        "What changes at the next gate?",
    ],
}

POOL_BY_INTENT = {
    "define": [
        "Which boundary makes this definition crisp?",
        "What is this not, precisely?",
    ],
    "compare": [
        "What criterion decides between them?",
        "Where do they diverge in purpose?",
    ],
    "troubleshoot": [
        "What broke first in the chain?",
        "Which assumption can you test fastest?",
    ],
    "guide": [
        "What is your next smallest honest step?",
        "What will you practice before asking more?",
    ],
    "ask": [
        "What would make this answer falsifiable?",
        "Which example would convince a skeptic?",
    ],
}

def _seed_from(q: str, draft: str, titles: list[str]) -> int:
    h = hashlib.sha256(("||".join([q or "", draft or ""] + (titles or []))).encode()).hexdigest()
    return int(h[:8], 16)

def _pick(seed: int, *pools: list[str]) -> str:
    rng = random.Random(seed)
    bag = [s for pool in pools for s in (pool or []) if s and s.strip()]
    if not bag:
        return "Which truth is asking to be seen now?"
    return rng.choice(bag)

def generate_guiding_question(
    q: str,
    draft: str,
    titles: list[str],
    route: RouteHint | None = None,
    keywords: list[str] | None = None,
) -> str:
    """Return a ≤12-word guiding question, varied but deterministic per (q,draft,titles)."""
    route = route or RouteHint()
    seed = _seed_from(q, draft, titles)

    qcanon = _canon(q)
    kws = set(keywords or [])
    for k in ["taboshi1", "taboshi", "satoby", "patience", "base", "epoch"]:
        if k in qcanon:
            kws.add(k)

    symbol_pool = POOL_BY_SYMBOL.get(route.symbol, [])
    intent_pool = POOL_BY_INTENT.get(route.intent, [])
    kw_pools = [POOL_BY_KEYWORD[k] for k in kws if k in POOL_BY_KEYWORD]

    if kw_pools:
        gq = _pick(seed, *kw_pools, symbol_pool, intent_pool, POOL_GENERIC)
    else:
        gq = _pick(seed, symbol_pool, intent_pool, POOL_GENERIC)

    # hard-cap 12 words
    words = gq.split()
    if len(words) > 12:
        gq = " ".join(words[:12])
    if not gq.endswith("?"):
        gq += "?"
    return gq

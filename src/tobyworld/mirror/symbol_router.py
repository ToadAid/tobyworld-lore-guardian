"""
Symbol Router — Mirror V3 (v0.1)

Purpose
-------
Route an incoming user query to one or more sub-agents using Tobyworld’s
symbolic vocabulary. Lightweight, deterministic, configurable.

Outputs a RouteResult with:
- primary_symbol (🌊/🌀/🍃/🪞)
- candidates (ranked with scores + reasons)
- intent ("qa" | "define" | "riddle" | "ops" | "scroll")
- depth (1..5)
- mode ("chat" | "scroll")
- tags + rationale (for logs/observability)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
import re

# -----------------------------
# Types
# -----------------------------
SemanticHook = Callable[[str, List[str]], List[float]]


@dataclass
class RouteCandidate:
    symbol: str
    score: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class RouteResult:
    primary_symbol: str
    candidates: List[RouteCandidate]
    intent: str  # "qa" | "define" | "riddle" | "ops" | "scroll"
    depth: int   # 1..5 heuristic
    mode: str    # "chat" | "scroll"
    tags: List[str] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)


# -----------------------------
# Config
# -----------------------------
DEFAULT_SYMBOL_MAP: Dict[str, Dict] = {
    # Water = onboarding, definitions, gentle guidance
    "🌊": {
        "aliases": ["water", "wave", "pond"],
        "keywords": [
            r"what is", r"define", r"meaning", r"how to start", r"beginner",
            r"onboard", r"overview", r"introduction", r"guide", r"explain",
            r"基础", r"是什么", r"怎么开始",
        ],
        "hashtags": ["#tobyworld", "#proofoftime", "#onboarding"],
        "sacred": [],
        "intent": "define",
        "agent": "gentle_guide",
    },
    # Vortex = deep philosophy, paradox, riddles
    "🌀": {
        "aliases": ["vortex", "spiral", "paradox", "zen"],
        "keywords": [
            r"why", r"paradox", r"riddle", r"koan", r"meaning of", r"destiny",
            r"silence", r"mirror", r"mind", r"信念", r"禅", r"道", r"意义",
        ],
        "hashtags": ["#lore", "#zen", "#oracle"],
        "sacred": ["777"],
        "intent": "riddle",
        "agent": "oracle_philosopher",
    },
    # Leaf = yield, Taboshi/Taboshi1, Satoby, PATIENCE mechanics
    "🍃": {
        "aliases": ["leaf", "taboshi", "yield"],
        "keywords": [
            r"taboshi1\??", r"taboshi 1", r"taboshi", r"satoby", r"yield",
            r"airdrop", r"claim", r"mint", r"burn", r"777", r"proof of time",
            r"PATIENCE", r"lotus", r"spores", r"leaf of yield", r"leaf of leaf",
            r"赎回", r"产出", r"收益", r"耐心",
        ],
        "hashtags": ["#taboshi", "#satoby", "#patience"],
        "sacred": ["777", "777,777,777"],
        "intent": "qa",
        "agent": "mechanics_scholar",
    },
    # Mirror = meta, system, epochs, runes, ops
    "🪞": {
        "aliases": ["mirror", "system", "agent", "router"],
        "keywords": [
            r"epoch", r"rune", r"E1", r"E2", r"E3", r"E4", r"season", r"vault",
            r"router", r"cadence", r"agentic", r"rag", r"index", r"miniapp",
            r"train", r"jsonl", r"dataset", r"pipeline", r"ops",
        ],
        "hashtags": ["#mirror", "#agent", "#rag"],
        "sacred": [],
        "intent": "ops",
        "agent": "ops_engineer",
    },
}

# Intent overrides by cue
INTENT_CUES = [
    (re.compile(r"^(make|write|generate) .*scroll", re.I), "scroll"),
    (re.compile(r"^act(?:ion)?:\s*scroll_?md", re.I), "scroll"),
    (re.compile(r"^/scroll\b", re.I), "scroll"),
]

# Depth cues (very rough)
DEPTH_CUES = [
    (re.compile(r"why|paradox|riddle|destiny|永恒|意义|禅|道", re.I), 4),
    (re.compile(r"how(\s+do|\s+to)?|mechanic|redeem|claim|eligib|合资格|规则", re.I), 3),
    (re.compile(r"what is|define|overview|guide|入门|是什么", re.I), 2),
]

# Mode cues
MODE_SCROLL = [
    re.compile(r"^/scroll|^act(?:ion)?:\s*scroll_?md|make .*scroll|write .*scroll", re.I)
]


# -----------------------------
# Utilities
# -----------------------------
def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _keyword_score(text: str, patterns: List[str]) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []
    for pat in patterns:
        if re.search(pat, text, re.I):
            score += 1.0
            reasons.append(f"kw:{pat}")
    return score, reasons


def _has_any(text: str, items: List[str]) -> Tuple[bool, List[str]]:
    hits: List[str] = []
    tl = text.lower()
    for it in items:
        if it.lower() in tl:
            hits.append(it)
    return (len(hits) > 0), hits


def _sacred_bonus(text: str, sacred: List[str]) -> Tuple[float, List[str]]:
    bonus = 0.0
    hits: List[str] = []
    for token in sacred:
        if token in text:
            bonus += 1.2
            hits.append(token)
    return bonus, [f"sacred:{h}" for h in hits]


def _symbol_presence_bonus(text: str, symbol: str, aliases: List[str]) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []
    if symbol in text:
        score += 2.0
        reasons.append(f"sym:{symbol}")
    for al in aliases:
        if re.search(rf"\b{re.escape(al)}\b", text, re.I):
            score += 0.6
            reasons.append(f"alias:{al}")
    return score, reasons


def _semantic_scores(text: str, labels: List[str], hook: Optional[SemanticHook]) -> List[float]:
    if hook is None:
        return [0.0] * len(labels)
    try:
        return hook(text, labels)
    except Exception:
        return [0.0] * len(labels)


def _rank(cands: List[RouteCandidate]) -> List[RouteCandidate]:
    return sorted(cands, key=lambda c: (-c.score, c.symbol))


# -----------------------------
# Router
# -----------------------------
class SymbolRouter:
    def __init__(self, symbol_map: Dict[str, Dict] | None = None, semantic_hook: SemanticHook | None = None):
        self.symbol_map = symbol_map or DEFAULT_SYMBOL_MAP
        self.semantic_hook = semantic_hook

    # --- public API ---
    def route(self, text: str) -> RouteResult:
        text_n = _normalize(text)
        cands = self._score_symbols(text_n)
        cands = _rank(cands)
        primary = cands[0].symbol if cands else "🌊"

        intent = self._infer_intent(text_n, primary)
        depth = self._infer_depth(text_n)
        mode = self._infer_mode(text_n)
        tags = self._derive_tags(primary, intent, depth)

        rationale: List[str] = []
        if cands:
            rationale.append(f"primary={primary} score={cands[0].score:.2f}")
            rationale.extend([f"{c.symbol}:{c.score:.2f} {'|'.join(c.reasons)}" for c in cands])

        return RouteResult(
            primary_symbol=primary,
            candidates=cands,
            intent=intent,
            depth=depth,
            mode=mode,
            tags=tags,
            rationale=rationale,
        )

    # --- internals ---
    def _score_symbols(self, text: str) -> List[RouteCandidate]:
        labels = list(self.symbol_map.keys())
        semantic = _semantic_scores(text, labels, self.semantic_hook)

        cands: List[RouteCandidate] = []
        for i, sym in enumerate(labels):
            cfg = self.symbol_map[sym]
            score = 0.0
            reasons: List[str] = []

            # presence + aliases
            p_score, p_r = _symbol_presence_bonus(text, sym, cfg.get("aliases", []))
            score += p_score; reasons += p_r

            # keywords
            k_score, k_r = _keyword_score(text, cfg.get("keywords", []))
            score += k_score; reasons += k_r

            # hashtags
            has_hit, has_hits = _has_any(text, cfg.get("hashtags", []))
            if has_hit:
                score += 0.6 * len(has_hits)
                reasons += [f"hash:{h}" for h in has_hits]

            # sacred bonuses
            s_bonus, s_r = _sacred_bonus(text, cfg.get("sacred", []))
            score += s_bonus; reasons += s_r

            # semantic hint
            if i < len(semantic):
                sem = float(semantic[i])
                # squash to [0..1.5]
                sem = max(0.0, min(1.0, sem)) * 1.5
                score += sem
                if sem > 0:
                    reasons.append(f"sem:{sem:.2f}")

            cands.append(RouteCandidate(symbol=sym, score=score, reasons=reasons))

        if not cands:
            cands = [RouteCandidate(symbol="🌊", score=0.0, reasons=["fallback"])]
        return cands

    def _infer_intent(self, text: str, primary: str) -> str:
        for pat, intent in INTENT_CUES:
            if pat.search(text):
                return intent
        return self.symbol_map.get(primary, {}).get("intent", "qa")

    def _infer_depth(self, text: str) -> int:
        depth = 1
        for pat, val in DEPTH_CUES:
            if pat.search(text):
                depth = max(depth, val)
        return min(depth, 5)

    def _infer_mode(self, text: str) -> str:
        for pat in MODE_SCROLL:
            if pat.search(text):
                return "scroll"
        return "chat"

    def _derive_tags(self, primary: str, intent: str, depth: int) -> List[str]:
        base = {
            "🌊": ["onboarding", "guide"],
            "🌀": ["philosophy", "oracle"],
            "🍃": ["mechanics", "yield"],
            "🪞": ["ops", "system"],
        }.get(primary, ["misc"])
        base.append(f"intent:{intent}")
        base.append(f"depth:{depth}")
        return base


# -----------------------------
# Minimal demo
# -----------------------------
if __name__ == "__main__":
    router = SymbolRouter()
    samples = [
        "what is taboshi1 and how do I redeem satoby?",
        "Why does destiny return to its beginning — paradox or perfection?",
        "/scroll make a lore scroll for the Trial of Patience (777).",
        "set up agentic rag router + cadence guard in bot_server",
    ]
    for s in samples:
        res = router.route(s)
        print("\nQ:", s)
        print("→ primary:", res.primary_symbol)
        print("→ intent:", res.intent, "depth:", res.depth, "mode:", res.mode)
        print("→ tags:", res.tags)
        print("→ rationale:")
        for r in res.rationale:
            print("  ", r)

"""
Cadence Guard — Mirror V3 (v0.2)
...
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Callable, Any
import re
import os

BUSHIDO_TENETS = ["勇", "仁", "礼", "誠", "忠", "名誉", "義"]

# NOTE: no guiding questions hardcoded; content comes from provider
SYMBOL_STYLES: Dict[str, Dict] = {
    "🌊": {"prefix": "Traveler,",  "tone": "gentle",        "emoji": ["🌊"]},
    "🌀": {"prefix": "You asked:", "tone": "contemplative", "emoji": ["🪞","🌀"]},
    "🍃": {"prefix": "Mechanics:", "tone": "precise",       "emoji": ["🍃"]},
    "🪞": {"prefix": "Operations:","tone": "clear",         "emoji": ["🪞"]},
}

SAFE_WORDS = [
    (re.compile(r"\bmoon|pump|lambo|guarantee|guaranteed|surefire\b", re.I), "Avoid hype wording."),
]

PROFANITY = re.compile(r"\b(f+u+c*k+|s+h+i+t+|b+i+t+c+h+|a+s+s+h+o+l+e+)\b", re.I)
MULTI_EXCL = re.compile(r"!{2,}")
ALL_CAPS   = re.compile(r"\b[A-Z]{6,}\b")
ZH_CHAR    = re.compile(r"[\u4e00-\u9fff]")

ENABLE_GQ  = os.getenv("MIRROR_GUIDING_QUESTION", "1") != "0"
_GQ_RX     = re.compile(r"(?i)\bGuiding\s*Question\s*:", re.UNICODE)

# ⛑️ ignore common stub strings
_STUB_RX   = re.compile(r"^(?:This is a stubbed scroll response\.?|Top hits:.*)$", re.I)

# Provider hook (installed by server.py)
_GUIDING_PROVIDER: Optional[Callable[[Any], str]] = None
def set_guiding_provider(fn: Optional[Callable[[Any], str]]) -> None:
    global _GUIDING_PROVIDER
    _GUIDING_PROVIDER = fn

def _detect_lang(s: str) -> str:
    return "zh" if ZH_CHAR.search(s) else "en"

def _collapse_whitespace(s: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", s or "")).strip()

def _bullets_to_clean(s: str) -> str:
    return re.sub(r"\n\s*[-•]\s*", "\n- ", s or "")

def _apply_symbol_adornments(symbol: str, text: str) -> str:
    st = SYMBOL_STYLES.get(symbol, SYMBOL_STYLES["🌊"])
    if not (text or "").lstrip().lower().startswith((st["prefix"].lower(),)):
        text = f"{st['prefix']}\n" + (text or "")
    return text

def _score(text: str) -> float:
    score = 1.0
    if PROFANITY.search(text): score -= 0.4
    if MULTI_EXCL.search(text): score -= 0.1
    if ALL_CAPS.search(text):   score -= 0.1
    for ln in (text or "").splitlines():
        if len(ln) > 240: score -= 0.05
    return max(0.0, min(1.0, score))

def _soft_rewrites(text: str) -> List[str]:
    notes: List[str] = []
    if PROFANITY.search(text):
        text = PROFANITY.sub("[softened]", text); notes.append("profanity softened")
    if MULTI_EXCL.search(text):
        text = MULTI_EXCL.sub("!", text);        notes.append("exclamation reduced")
    if ALL_CAPS.search(text):
        text = ALL_CAPS.sub(lambda m: m.group(0).title(), text); notes.append("caps normalized")
    return [text, *notes]

def _inject_bushido_footer(text: str, lang: str) -> str:
    footer = ("\n\n— 七德：勇 · 仁 · 礼 · 誠 · 忠 · 名誉 · 義"
              if lang == "zh" else
              "\n\n— Bushido: Courage · Compassion · Courtesy · Sincerity · Loyalty · Honor · Righteousness")
    if footer.strip() not in (text or ""):
        text = (text or "") + footer
    return text

def enforce(route, text: str, user_lang_hint: Optional[str] = None, strict: bool = False):
    lang = user_lang_hint or _detect_lang(text)

    out = _collapse_whitespace(text)
    out = _bullets_to_clean(out)

    rew = _soft_rewrites(out); out, notes = rew[0], list(rew[1:])
    out = _apply_symbol_adornments(getattr(route, "primary_symbol", "🌊"), out)

    if strict:
        new_lines = []
        for ln in (out or "").splitlines():
            if len(ln) > 240:
                new_lines.extend([ln[i:i+120] for i in range(0, len(ln), 120)])
                notes.append("long lines wrapped")
            else:
                new_lines.append(ln)
        out = "\n".join(new_lines)

    # Guiding Question (from provider), skip stubs
    if ENABLE_GQ and not _GQ_RX.search(out or "") and _GUIDING_PROVIDER is not None:
        try:
            gq = (_GUIDING_PROVIDER(route) or "").strip()
        except Exception:
            gq = ""
        if gq and not _STUB_RX.search(gq):
            if not gq.endswith("?"):
                gq += "?"
            out = out.rstrip() + f"\n\n**Guiding Question:** {gq}"

    out = _inject_bushido_footer(out, lang)

    score = _score(out)
    ok = score >= (0.7 if not strict else 0.8)

    style = SYMBOL_STYLES.get(getattr(route, "primary_symbol", "🌊"))
    if style:
        em = " ".join(style.get("emoji", [])[:2])
        if em and em not in (out or ""):
            out = f"{out}\n{em}"

    return ok, out, notes, score

if __name__ == "__main__":
    class DummyRoute:
        def __init__(self, sym): self.primary_symbol=sym; self.intent="qa"; self.depth=3
    def demo_provider(route): return "What is your first step?"
    set_guiding_provider(demo_provider)
    ok, final, notes, score = enforce(DummyRoute("🍃"), "I GUARANTEE you!!\n- burn 777\n- wait\n- claim")
    print("OK?", ok, "score=", score); print("notes:", notes); print("---\n", final)

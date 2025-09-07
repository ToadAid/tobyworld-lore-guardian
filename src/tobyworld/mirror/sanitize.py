# tobyworld/mirror/sanitize.py
from __future__ import annotations
import re

_RE_FILE  = re.compile(r"(?<!\w)[\w\-./]*\.(?:md|txt)(?!\w)", re.I)
_RE_TOBY  = re.compile(r"\bTOBY[_A-Z0-9\-]*\b", re.I)
_RE_REF   = re.compile(r"\[ref:\s*\d+\]", re.I)
_RE_TOP   = re.compile(r"\bTop hits:\s*.*", re.I)
_RE_STUB  = re.compile(r"This is a stubbed scroll response\.", re.I)
_RE_BUSH  = re.compile(r"—\s*Bushido:.*", re.I)

_RE_NOISE_LINE = re.compile(r"^\s*(?:[🌊🪞🍃🌀📜\s]+|You asked:.*|Guiding\s*Question\s*:.*)\s*$", re.I)

def _unwrap_soft_breaks(s: str) -> str:
    s = s.replace("\r\n", "\n")
    s = re.sub(r"\n{2,}", "\u2029", s)
    s = re.sub(r"([A-Za-z])\n([A-Za-z])", r"\1\2", s)
    s = re.sub(r"(?<![.!?:;])\n(?!\n)", " ", s)
    s = s.replace("\u2029", "\n\n")
    return s

def sanitize(text: str) -> str:
    if not text:
        return ""
    t = _unwrap_soft_breaks(text)

    # strip crumbs
    t = _RE_FILE.sub("", t)
    t = _RE_TOBY.sub("", t)
    t = _RE_REF.sub("", t)
    t = _RE_TOP.sub("", t)
    t = _RE_STUB.sub("", t)
    t = _RE_BUSH.sub("", t)

    # orphaned citation leads
    t = re.sub(r'\b(?:In|As stated in|As seen in|According to)\s*[:：]?\s*(?=(?:,|\.|\n|$))', "", t, flags=re.I)
    # empty quoted titles like: In "" ,  or  In ""
    t = re.sub(r'"\s*"', "", t)

    # NEW: ultra-safe fused-word fixes (observed cases only)
    fused = {
        r"\bdiebut\b": "die but",
        r"\bwherenone\b": "where none",
        r"\bconquerbut\b": "conquer but",
        r"\btimetransforms\b": "time transforms",
        r"\bfourrunes\b": "four runes",
        r"\bletit\b": "let it",
    }
    for pat, rep in fused.items():
        t = re.sub(pat, rep, t, flags=re.I)

    # kill orphan phrases like "as mentioned in ."
    t = re.sub(r"\b(as\s+(?:mentioned|seen|stated|noted)\s+in)\s*[.,]", "", t, flags=re.I)

    # drop pure-noise lines
    lines = [ln for ln in t.splitlines() if not _RE_NOISE_LINE.match(ln)]
    t = "\n".join(lines)

    # tidy spaces/punctuation
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t

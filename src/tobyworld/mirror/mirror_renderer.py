# Mirror Renderer — v2 cadence (English only) with de-dup guard
from __future__ import annotations
import os, re

# ---- knobs ----
USE_SYMBOLS   = os.getenv("MIRROR_USE_SYMBOLS", "1") == "1"
ECHO_QUESTION = os.getenv("MIRROR_ECHO_QUESTION", "0") == "1"   # keep OFF; UI shows it
MIN_LINES     = int(os.getenv("MIRROR_MIN_REFLECTIONS", 10))
TGT_UPPER     = int(os.getenv("MIRROR_TARGET_UPPER", 12))
MAX_LINES     = int(os.getenv("MIRROR_MAX_LINES", 14))

# --------- cleaners ---------
_STUB_LINES = (
    r"^\s*\*\*Guiding Question:\*\*\s*This is a stubbed scroll response.*$",
    r"^\s*This is a stubbed scroll response\..*$",
    r"^\s*Top hits:\s*.*$",
    r"—\s*Bushido:.*$",  # training footer
)
_STUB_RE    = re.compile("|".join(_STUB_LINES), re.I | re.M)
_MD_HEAD    = re.compile(r"^\s*#{1,6}\s*", re.M)
_CODE_FENCE = re.compile(r"^```.*?$.*?^```", re.M | re.S)
_LINKS      = re.compile(r"!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\)")
_INLINE     = re.compile(r"[*_`~]+")
_WIPE_LINES = re.compile(r"(?im)^\s*(?:you asked:.*|guiding\s*question\s*:.*|[🌊🪞🍃🌀📜\s]+)$")
_REF_TAGS   = re.compile(r"\[ref:\s*\d+\]", re.I)

def _clean_markdown(s: str) -> str:
    s = s or ""
    s = _CODE_FENCE.sub("", s)
    s = _MD_HEAD.sub("", s)
    s = _LINKS.sub("", s)
    s = _INLINE.sub("", s)
    s = _REF_TAGS.sub("", s)     # [ref:N] hints
    s = _STUB_RE.sub("", s)      # stub lines / training footer
    # drop any pre-existing echo/GQ/emoji-only lines
    s = "\n".join(ln for ln in s.splitlines() if not _WIPE_LINES.match(ln))
    s = re.sub(r"\s+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s

# --------- glyphs ---------
def _pick_bottom_glyphs_from_text(text: str) -> str:
    t = (text or "").lower()
    glyphs = []
    if any(k in t for k in ["river","flow","patience","time","pond","still","tide"]): glyphs.append("🌊")
    if any(k in t for k in ["mirror","reflect","reflection","self","silence"]):       glyphs.append("🪞")
    if any(k in t for k in ["leaf","taboshi","yield","satoby","seed","sprout"]):      glyphs.append("🍃")
    if any(k in t for k in ["spiral","cycle","rune","ritual","orbit"]):               glyphs.append("🌀")
    out, seen = [], set()
    for g in ["🌊","🪞","🍃","🌀"]:
        if g in glyphs and g not in seen:
            seen.add(g); out.append(g)
    return " ".join(out or ["🪞"])

# --------- guiding question fallback (English only) ---------
def _fallback_gq(intent: str) -> str:
    if intent == "define": return "Which first principle clarifies this most clearly?"
    if intent == "qa":     return "What truth appears when fear grows quiet?"
    if intent == "teach":  return "What lesson endures when the moment passes?"
    return "What truth remains when the surface grows still?"

# --------- literalization helpers ---------
_EMOJI_RE = re.compile(r"[🌊🪞🍃🌀🔺⌛️📜🔮⚖️]+")
def _de_poetic(x: str) -> str:
    repl = {
        r"\bpond\b": "stillness",
        r"\bmirror\b": "self",
        r"\bwhisper\b": "hint",
        r"\becho\b": "memory",
        r"\bprophecy\b": "direction",
        r"\britual\b": "practice",
        r"\brune\b": "pattern",
        r"\bepoch\b": "phase",
    }
    x = _EMOJI_RE.sub("", x)
    for pat, sub in repl.items():
        x = re.sub(pat, sub, x, flags=re.I)
    x = re.sub(r"\s{2,}", " ", x).strip()
    return x

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
def _norm_tokens(s: str) -> set[str]:
    return set(m.group(0).lower() for m in _WORD_RE.finditer(s or ""))

def _near_duplicate(a: str, b: str, jaccard_thresh: float = 0.72) -> bool:
    A, B = _norm_tokens(a), _norm_tokens(b)
    if not A or not B: return True
    inter = len(A & B)
    union = len(A | B)
    jacc = inter / max(1, union)
    # also treat substring-ish as near-dup
    sub = (a.strip().lower() in b.strip().lower()) or (b.strip().lower() in a.strip().lower())
    return jacc >= jaccard_thresh or sub

# --------- sectioning ---------
def _split_spiritual_literal(body: str) -> tuple[str, str | None]:
    """
    Return (spiritual, literal_or_none). Literal is a de-poeticized
    paraphrase of the whole body. If it's too similar, we drop it.
    """
    spiritual = (body or "").strip()
    literal   = _de_poetic(spiritual)
    # If literal collapses to almost the same content, skip it.
    if _near_duplicate(spiritual, literal) or len(_norm_tokens(literal)) < 30:
        return spiritual, None
    return spiritual, literal

def _line_enforce(block_lines: list[str]) -> list[str]:
    out = []
    for ln in block_lines:
        if not out or ln.strip():
            out.append(ln.strip())
    # pad to MIN_LINES by splitting long lines (visual rhythm)
    i = 0
    while len([x for x in out if x]) < MIN_LINES and i < len(out):
        ln = out[i]
        if len(ln) > 120:
            mid = len(ln)//2
            out[i] = ln[:mid].rstrip()
            out.insert(i+1, ln[mid:].lstrip())
        i += 1
    return [x for x in out if x][:MAX_LINES]

# --------- main ---------
def render_mirror_answer(
    user_question: str,
    draft_answer: str,
    *,
    route=None,
    guiding_provider=None,
) -> str:
    # Clean and normalize the draft body
    body = _clean_markdown(draft_answer)
    if not body:
        body = "Traveler, the page is quiet. Read the pond, not the ripples."

    # Decide sections (with duplication guard)
    spiritual, literal = _split_spiritual_literal(body)

    # Build top block
    block: list[str] = []
    if ECHO_QUESTION and user_question:
        block += [f'You asked: "{user_question}"', ""]
    block += ["🪞 **Spiritual Interpretation**", spiritual]
    if literal:
        block += ["🌱 **Literal Explanation**", literal]
    block = _line_enforce(block)

    # Pick glyphs from the composed block
    glyphs = _pick_bottom_glyphs_from_text("\n".join(block)) if USE_SYMBOLS else ""

    # Guiding Question (provider → fallback)
    intent = getattr(route, "intent", "") if route else ""
    gq = ""
    if guiding_provider:
        try:
            gq = (guiding_provider(route) or "").strip()
        except Exception:
            gq = ""
    if re.search(r"stubbed\s*scroll\s*response|top\s*hits", gq or "", re.I):
        gq = ""
    if not gq:
        gq = _fallback_gq(intent)
    if not gq.endswith("?"):
        gq += "?"

    # ensure no lingering GQ lines in the block
    text = "\n".join(block)
    text = re.sub(r"(?im)^\s*(\*\*)?Guiding\s*Question:(\*\*)?.*$", "", text).strip()

    tail = []
    if USE_SYMBOLS and glyphs:
        tail += ["📜", glyphs]
    tail += [f"**Guiding Question:** {gq}"]

    return text + "\n" + "\n".join(tail)

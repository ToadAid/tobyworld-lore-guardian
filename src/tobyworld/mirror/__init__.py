"""
Mirror V3 package
=================
Convenience exports + tiny helpers so the app can import from
`tobyworld.mirror` directly.

Usage
-----
from tobyworld.mirror import SymbolRouter, guard_enforce
router = SymbolRouter()
route = router.route(user_text)
# ... generate draft with your selected agent ...
ok, final_text, notes, score = guard_enforce(route, draft)
"""
from .symbol_router import SymbolRouter, RouteResult, RouteCandidate
from .cadence_guard import enforce as guard_enforce

__all__ = [
    "SymbolRouter",
    "RouteResult",
    "RouteCandidate",
    "guard_enforce",
    "get_default_router",
    "apply_guard",
]


def get_default_router(semantic_hook=None) -> SymbolRouter:
    """Factory for a default SymbolRouter (optionally pass a semantic hook)."""
    return SymbolRouter(semantic_hook=semantic_hook)


def apply_guard(route: RouteResult, draft_text: str, *, user_lang_hint=None, strict: bool | None = None):
    """Convenience wrapper around cadence guard.

    If `strict` is None, it auto‑enables strict mode for deep queries (depth ≥ 4).
    Returns (ok: bool, revised_text: str, notes: list[str], score: float)
    """
    if strict is None:
        strict = getattr(route, "depth", 1) >= 4
    return guard_enforce(route, draft_text, user_lang_hint=user_lang_hint, strict=strict)

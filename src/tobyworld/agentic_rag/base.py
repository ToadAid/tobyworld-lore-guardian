# src/tobyworld/agentic_rag/base.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, List, Dict, Any, Optional
import time


# -----------------------------
# Core data containers
# -----------------------------
@dataclass
class DocBlob:
    doc_id: str
    text: str
    meta: Dict[str, Any]
    score: float = 0.0


@dataclass
class QueryContext:
    user_id: str
    user_lang_hint: Optional[str] = None
    route_symbol: Optional[str] = None  # 🍃/🌀/🌊/🪞
    depth: str = "normal"
    # Use default_factory so "now" is captured at instance creation, not import time
    now: float = field(default_factory=lambda: time.time())
    # Avoid mutable default args
    extra: Dict[str, Any] = field(default_factory=dict)


# -----------------------------
# Interfaces / Protocols
# -----------------------------
class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[DocBlob]:
        ...


class Reranker(Protocol):
    def rerank(self, query: str, docs: List[DocBlob], top_k: Optional[int] = None) -> List[DocBlob]:
        ...


class LLM(Protocol):
    def complete(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        ...


# -----------------------------
# Orchestration helpers
# -----------------------------
@dataclass
class Circuit:
    max_steps: int = 3
    max_tokens_ctx: int = 6000
    enabled: bool = True

    def allow_step(self, step: int) -> bool:
        return (not self.enabled) or (step < self.max_steps)

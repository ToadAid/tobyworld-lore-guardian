# src/tobyworld/agentic_rag/multi_arc_retrieval.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Iterable
import re
import math

from .base import DocBlob  # (id, text, meta, score)


# -------------------------
# Configs / Interfaces
# -------------------------
@dataclass
class ArcConfig:
    name: str
    weight: float = 1.0
    k: int = 8
    enabled: bool = True


class Retriever:
    """Interface for retrieval backends."""
    def retrieve(self, query: str, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[DocBlob]:
        raise NotImplementedError


# -----------------------------------------
# Local lexical retriever (fast + simple)
# -----------------------------------------
class LocalRetriever(Retriever):
    """
    In-memory lexical retriever over a list of rows shaped like:
      {"id": str, "text": str, "meta": {...}}
    Scoring:
      - term frequency over tokenized text
      - +2.0 bonus if the full lowercased query phrase appears
      - small title hit bonus (+1.0) if any token hits in title
    """

    _TOKEN_RX = re.compile(r"[A-Za-z0-9_#@]+")

    def __init__(self, index_rows: List[Dict[str, Any]]):
        self.rows = index_rows or []

    @staticmethod
    def _tok(s: str) -> List[str]:
        return LocalRetriever._TOKEN_RX.findall((s or "").lower())

    def _score_row(self, row: Dict[str, Any], q_tokens: List[str], q_phrase: str) -> float:
        text = (row.get("text") or "")
        if not text:
            return 0.0
        tokens = self._tok(text)
        if not tokens:
            return 0.0
        tf = sum(tokens.count(t) for t in set(q_tokens))
        bonus = 2.0 if (q_phrase and q_phrase in text.lower()) else 0.0
        # title bonus
        title = str(((row.get("meta") or {}).get("title") or "")).lower()
        title_bonus = 0.0
        if title:
            if any(t in title for t in q_tokens):
                title_bonus = 1.0
        return float(tf) + bonus + title_bonus

    def retrieve(self, query: str, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[DocBlob]:
        q = (query or "").strip().lower()
        if not q:
            return []
        q_tokens = self._tok(q)
        if not q_tokens:
            return []
        q_phrase = " ".join(q_tokens)

        scored: List[DocBlob] = []
        for row in self.rows:
            s = self._score_row(row, q_tokens, q_phrase)
            if s <= 0.0:
                continue
            scored.append(DocBlob(
                doc_id=row.get("id") or "",
                text=row.get("text") or "",
                meta=row.get("meta") or {},
                score=s,
            ))

        scored.sort(key=lambda d: (-d.score, d.doc_id))
        return scored[: max(1, k)] if scored else []


# -----------------------------------------
# Multi-arc retrieval & merge
# -----------------------------------------
class MultiArcRetriever(Retriever):
    """
    Fan out to multiple arcs (e.g., 'lexical', 'dense'), merge scores by doc_id,
    and return the top-k. Exposes lightweight stats for debugging:
      self.last_stats = {
        "per_arc": {"lexical": 12, "dense": 8, ...},
        "unique_before_cut": 17,
        "returned": 8
      }
    """

    def __init__(self, arcs: Dict[str, ArcConfig], backends: Dict[str, Retriever]):
        self.arcs = arcs or {}
        self.backends = backends or {}
        self.last_stats: Dict[str, Any] = {}

    def retrieve(self, query: str, k: int = 8, filters: Optional[Dict[str, Any]] = None) -> List[DocBlob]:
        bucket: Dict[str, DocBlob] = {}
        stats = {"per_arc": {}, "unique_before_cut": 0}

        for name, cfg in self.arcs.items():
            if not cfg.enabled:
                continue
            backend = self.backends.get(name)
            if not backend:
                continue
            try:
                hits = backend.retrieve(query, k=cfg.k, filters=filters)
            except Exception:
                hits = []
            stats["per_arc"][name] = len(hits)
            for h in hits:
                wscore = float(h.score) * float(cfg.weight)
                if h.doc_id in bucket:
                    # soft-union by max-like add (simple sum is fine here)
                    bucket[h.doc_id].score = bucket[h.doc_id].score + wscore
                else:
                    bucket[h.doc_id] = DocBlob(h.doc_id, h.text, h.meta, wscore)

        merged = list(bucket.values())
        stats["unique_before_cut"] = len(merged)
        merged.sort(key=lambda x: x.score, reverse=True)
        out = merged[:k]

        self.last_stats = stats | {"returned": len(out)}
        return out

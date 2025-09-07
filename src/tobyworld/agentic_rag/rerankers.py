# src/tobyworld/agentic_rag/rerankers.py
from __future__ import annotations

from typing import List, Dict, Any, Optional
import math
import re

from .base import DocBlob  # (doc_id, text, meta, score)


class Reranker:
    """Interface: take (query, docs) → re-order with optional cut to top_k."""
    def rerank(self, query: str, docs: List[DocBlob], top_k: Optional[int] = None) -> List[DocBlob]:
        raise NotImplementedError


class KeywordCosineReranker(Reranker):
    """
    Lightweight lexical reranker:
      • Build sparse token→tf dicts for query and doc snippets (title+body head)
      • Cosine similarity
      • Final score = 0.7 * prior_score + 0.3 * cosine
    Notes:
      • No external deps
      • Tokenizer matches LocalRetriever so signals align
    """

    _TOK = re.compile(r"[A-Za-z0-9_#@]+")

    def __init__(self, doc_chars: int = 800, title_weight: float = 1.25,
                 alpha_prior: float = 0.7):
        self.doc_chars = int(doc_chars)
        self.title_weight = float(title_weight)
        self.alpha_prior = float(alpha_prior)

    @staticmethod
    def _tok(s: str) -> List[str]:
        return KeywordCosineReranker._TOK.findall((s or "").lower())

    @staticmethod
    def _tf(tokens: List[str]) -> Dict[str, float]:
        tf: Dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0
        # l2 normalize
        norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
        for k in tf:
            tf[k] /= norm
        return tf

    @staticmethod
    def _cos(qv: Dict[str, float], dv: Dict[str, float]) -> float:
        # dot product over intersection
        if len(qv) > len(dv):
            qv, dv = dv, qv
        dot = 0.0
        for k, v in qv.items():
            dvk = dv.get(k)
            if dvk is not None:
                dot += v * dvk
        # clamp numeric noise
        if dot < 0.0: dot = 0.0
        if dot > 1.0: dot = 1.0
        return dot

    def _doc_tokens(self, d: DocBlob) -> List[str]:
        meta = d.meta or {}
        title = (meta.get("title") or "") if isinstance(meta, dict) else ""
        body = (d.text or "")[: self.doc_chars]
        toks = self._tok(body)
        if title:
            # add weighted title tokens
            tt = self._tok(title)
            toks.extend(tt * max(1, int(self.title_weight)))
        return toks

    def rerank(self, query: str, docs: List[DocBlob], top_k: Optional[int] = None) -> List[DocBlob]:
        if not docs:
            return []
        q_tokens = self._tok(query or "")
        if not q_tokens:
            # nothing to compare; keep prior ordering and cut
            out = list(docs)
            if top_k is not None:
                out = out[: max(1, top_k)]
            return out

        qv = self._tf(q_tokens)

        rescored: List[DocBlob] = []
        for d in docs:
            dv = self._tf(self._doc_tokens(d))
            cos = self._cos(qv, dv)
            # blend prior retrieval score with cosine
            combined = self.alpha_prior * float(d.score) + (1.0 - self.alpha_prior) * cos
            rescored.append(DocBlob(d.doc_id, d.text, d.meta, combined))

        rescored.sort(key=lambda x: x.score, reverse=True)
        if top_k is not None:
            rescored = rescored[: max(1, top_k)]
        return rescored

# src/tobyworld/agentic_rag/pipeline.py
from __future__ import annotations

from typing import Dict, Any, Optional, List

from .base import QueryContext, DocBlob, Circuit
from .multi_arc_retrieval import MultiArcRetriever
from .rerankers import KeywordCosineReranker
from .reasoning_agent import ReasoningAgent
from .synthesis_agent import SynthesisAgent
from .learning import LearningStore, LearningEvent
from tobyworld.traits.resonance import Rescorer, HalfLifeRescorer
from tobyworld.traits.lucidity import Lucidity


# ---- Hard-coded v2-like budgets (no env needed) ----------------------
TOPK_FINAL        = 24     # combined shortlist cap from retriever
NOTES_USED        = 6      # docs merged into synthesis
PER_NOTE_CHARS    = 1200   # excerpt budget per doc
CTX_CHARS_TOTAL   = 6000   # overall context char target
SYNTH_MAX_TOKENS  = 2000   # ~2k tokens for synthesis (≈ CTX_CHARS_TOTAL/3)
# ---------------------------------------------------------------------


class AgenticRAGPipeline:
    def __init__(
        self,
        retriever: MultiArcRetriever,
        reasoning: ReasoningAgent,
        synthesis: SynthesisAgent,
        reranker: Optional[KeywordCosineReranker] = None,
        circuit: Optional[Circuit] = None,
        learning_store: Optional[LearningStore] = None,
        rescorer: Optional[Rescorer] = None,
    ):
        self.retriever = retriever
        self.reasoning = reasoning
        self.synthesis = synthesis
        self.reranker = reranker or KeywordCosineReranker()
        self.circuit = circuit or Circuit(max_steps=3)
        self.learning = learning_store or LearningStore()
        self.rescorer = rescorer or HalfLifeRescorer(self.learning)
        # Lucidity tracker (EWMA over engagement/clarity)
        self.lucidity = Lucidity()

    def run(
        self,
        query: str,
        ctx: QueryContext,
        k: int = 8,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        filters = filters or {}

        # Resolve budgets (server may pass overrides in filters; else use constants)
        topk_final     = min(int(k or TOPK_FINAL), TOPK_FINAL)
        notes_used     = int(filters.get("use_docs", NOTES_USED))
        per_note_chars = int(filters.get("per_note_chars", PER_NOTE_CHARS))

        # ---- Stage A: initial retrieve (per-arc + unique) -------------------
        docs = self.retriever.retrieve(query, k=topk_final, filters=filters)
        rstats = getattr(self.retriever, "last_stats", {})
        stage_counts = {
            "arcs": rstats.get("per_arc", {}),
            "unique_before_cut": rstats.get("unique_before_cut", len(docs)),
            "returned_from_retriever": rstats.get("returned", len(docs)),
        }

        # ---- Stage B: resonance (half-life decay + learning boost) ----------
        docs = self.rescorer.rescore(query, docs)
        stage_counts["after_resonance"] = len(docs)

        # ---- Stage C: rerank (keyword cosine) and shortlist -----------------
        # keep a generous shortlist here; final cut happens below
        rerank_cap = max(notes_used, min(topk_final, 12))
        docs = self.reranker.rerank(query, docs, top_k=rerank_cap)
        stage_counts["after_rerank"] = len(docs)

        # ---- Stage D: optional deep reasoning refinement --------------------
        if ctx.depth == "deep" and self.circuit.allow_step(0):
            thoughts, refined = self.reasoning.analyze(query, ctx, docs)
            stage_counts["refined_used"] = bool(refined and refined != query)
            if refined and refined != query:
                ref_docs = self.retriever.retrieve(refined, k=topk_final, filters=filters)
                ref_docs = self.reranker.rerank(refined, ref_docs, top_k=rerank_cap)
                docs = self._blend(docs, ref_docs, top_k=rerank_cap)
                stage_counts["after_blend"] = len(docs)

        # ---- Stage E: final cut & excerpt budget ----------------------------
        use_docs = docs[:notes_used]

        # Trim excerpts to per_note_chars without breaking existing fields
        for d in use_docs:
            # prefer DocBlob.text, else DocBlob.content, else meta["excerpt"]
            if hasattr(d, "text") and isinstance(d.text, str):
                d.text = d.text[:per_note_chars]
            elif hasattr(d, "content") and isinstance(d.content, str):
                d.content = d.content[:per_note_chars]
            else:
                meta = getattr(d, "meta", None) or {}
                ex = meta.get("excerpt") or meta.get("text") or ""
                meta["excerpt"] = str(ex)[:per_note_chars]
                d.meta = meta  # ensure write-back

        # ---- Stage F: synthesis (compose final answer) ----------------------
        # Try newer compose signature first: (query, ctx, docs, max_tokens=..)
        try:
            answer, used_refs, tone_score = self.synthesis.compose(
                query, ctx, use_docs, max_tokens=SYNTH_MAX_TOKENS
            )
        except TypeError:
            # Fallback to older signature: (query, ctx, docs)
            answer, used_refs, tone_score = self.synthesis.compose(query, ctx, use_docs)

        # ---- Lucidity (ENGAGEMENT x CLARITY) --------------------------------
        used_count = len(used_refs or []) if used_refs is not None else len(use_docs)
        engagement = min(1.0, used_count / max(1, notes_used))  # scale vs planned used docs
        clarity = float(tone_score or 0.0)
        lucidity_level, lucidity_traits = self.lucidity.adjust(engagement, clarity)

        result = {
            "answer": answer,
            "used_refs": used_refs,
            "tone_score": tone_score,
            "docs": [{"id": d.doc_id, "score": round(float(d.score), 4), "meta": d.meta} for d in use_docs],
            "stats": stage_counts | {
                "used_docs": len(use_docs),
                "target_tokens": SYNTH_MAX_TOKENS,
                "lucidity_level": lucidity_level,
                "lucidity_traits": lucidity_traits,
                "engagement": round(engagement, 3),
                "clarity": round(clarity, 3),
            },
        }

        # ---- Stage G: learning event (non-blocking) -------------------------
        try:
            self.learning.record(LearningEvent(
                ts=getattr(ctx, "now", None) or __import__("time").time(),
                user_id=ctx.user_id,
                route_symbol=ctx.route_symbol or "🪞",
                query=query,
                answer_preview=(answer or "")[:240],
                used_doc_ids=[d.doc_id for d in use_docs],
                used_doc_titles=[(d.meta or {}).get("title", "") for d in use_docs],
                tone_score=float(tone_score or 0.0),
                extra={"depth": ctx.depth, "stats": result["stats"]},
            ))
        except Exception:
            # Learning must never break answers
            pass

        return result

    @staticmethod
    def _blend(a: List[DocBlob], b: List[DocBlob], top_k: int = 8) -> List[DocBlob]:
        """Merge two ranked lists by doc_id, keeping the max score per id."""
        bucket: Dict[str, DocBlob] = {}
        for lst in (a, b):
            for d in lst:
                if d.doc_id in bucket:
                    if d.score > bucket[d.doc_id].score:
                        bucket[d.doc_id] = d
                else:
                    bucket[d.doc_id] = d
        merged = list(bucket.values())
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:top_k]

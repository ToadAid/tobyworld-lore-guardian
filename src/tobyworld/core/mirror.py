from __future__ import annotations
from pathlib import Path
from typing import Tuple, Dict, Any

from .config import Config
from .ledger import Ledger
from ..retrieval.retriever import Retriever

try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except Exception:
    _HAS_ST = False

class MirrorCore:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.ledger = Ledger()

        self.index_dir = Path(self.cfg.data_dir) / "index"
        self.retriever = Retriever(self.index_dir)

        emb_model = getattr(self.cfg, "embedding_model", "all-MiniLM-L6-v2")
        self.embedder = SentenceTransformer(emb_model) if _HAS_ST else None
        self.rag_top_k = int(getattr(self.cfg, "rag_top_k", 5))

    def ask(self, user: str, question: str) -> Tuple[str, Dict[str, Any]]:
        if not question:
            return ("", {"error": "empty question"})

        docs_used = 0
        answer = "This is a stubbed scroll response."

        if self.retriever.ready and self.embedder is not None:
            qv = self.embedder.encode([question], convert_to_numpy=True, normalize_embeddings=True)[0]
            hits = self.retriever.search_embedding(qv, top_k=self.rag_top_k)
            docs_used = len(hits)
            if hits:
                top = ", ".join(Path(h.path).name for h in hits[:3])
                answer = f"{answer}\nTop hits: {top}"

        self.ledger.add("ask", {"user": user, "flags": {}, "docs": docs_used, "lucidity": "ENGAGED"})
        return (answer, {"lucidity": "ENGAGED", "docs_used": docs_used})

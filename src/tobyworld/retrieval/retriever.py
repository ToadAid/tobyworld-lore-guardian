from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import json
import numpy as np

try:
    import faiss  # type: ignore
    _HAS_FAISS = True
except Exception:
    _HAS_FAISS = False

@dataclass
class Hit:
    path: str
    chunk: int
    score: float

class Retriever:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.ready = False
        self._embs: Optional[np.ndarray] = None
        self._meta: Optional[Dict[str, Any]] = None
        self._faiss = None
        self._load()

    def _load(self):
        meta_p = self.index_dir / "meta.json"
        embs_p = self.index_dir / "embeddings.npy"
        if not meta_p.exists() or not embs_p.exists():
            return
        with meta_p.open("r", encoding="utf-8") as f:
            self._meta = json.load(f)
        self._embs = np.load(embs_p)
        if _HAS_FAISS:
            faiss_p = self.index_dir / "vectors.faiss"
            if faiss_p.exists():
                self._faiss = faiss.read_index(str(faiss_p))
        self.ready = True

    def search_embedding(self, q: np.ndarray, top_k: int = 5) -> List[Hit]:
        if not self.ready or self._embs is None or self._meta is None:
            return []
        q = q.astype(np.float32)
        # assume embeddings are normalized → cosine via inner product
        if self._faiss is not None:
            D, I = self._faiss.search(q.reshape(1, -1), top_k)
            idxs = I[0].tolist()
            scores = D[0].tolist()
        else:
            sims = (self._embs @ q.reshape(-1, 1)).ravel()
            idxs = np.argsort(-sims)[:top_k].tolist()
            scores = sims[idxs].tolist()

        items = self._meta.get("items", [])
        out: List[Hit] = []
        for i, s in zip(idxs, scores):
            if i < 0 or i >= len(items):
                continue
            it = items[i]
            out.append(Hit(path=it["path"], chunk=it["chunk"], score=float(s)))
        return out

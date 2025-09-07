# src/tobyworld/retrieval/pluggable.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Tuple
import re

# ----- Base protocol -----
class BaseRetriever:
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError

# ----- Local (existing) -----
class LocalRetriever(BaseRetriever):
    def __init__(self, root: Path):
        self.base = root
        self._cache: Dict[Path, str] = {}
        self._index: List[Path] = []
        self._build_index()

    def _build_index(self):
        exts = {".md", ".markdown", ".txt"}
        self._index = sorted(p for p in self.base.rglob("*") if p.is_file() and p.suffix.lower() in exts)

    def _read(self, p: Path) -> str:
        s = self._cache.get(p)
        if s is None:
            try:
                s = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                s = ""
            self._cache[p] = s
        return s

    @staticmethod
    def _tok(s: str): return re.findall(r"[A-Za-z0-9_#@]+", s.lower())
    def _score(self, text: str, qtok: List[str]) -> float:
        t = self._tok(text)
        if not t: return 0.0
        tf = sum(t.count(x) for x in set(qtok))
        phrase = " ".join(qtok)
        return float(tf) + (2.0 if phrase and phrase in text.lower() else 0.0)

    @staticmethod
    def _first(text: str, n=200):
        for ln in text.splitlines():
            ln = ln.strip()
            if ln: return (ln[:n-3]+"...") if len(ln)>n else ln
        return text[:n]

    @staticmethod
    def _nice_title(path: Path, text: str) -> str:
        for ln in text.splitlines():
            if ln.strip().startswith("#"):
                return re.sub(r"^#+\\s*", "", ln).strip()
        return path.stem.replace("_"," ").replace("-"," ").strip() or path.name

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        qtok = self._tok(query)
        scored: List[Tuple[float, Path]] = []
        for p in self._index:
            tx = self._read(p)
            sc = self._score(tx, qtok)
            if sc > 0: scored.append((sc, p))
        scored.sort(key=lambda x: (-x[0], str(x[1])))
        hits = []
        for sc, p in scored[:max(1, top_k)]:
            tx = self._read(p)
            hits.append({
                "title": self._nice_title(p, tx),
                "path": str(p),
                "score": round(sc, 3),
                "snippet": self._first(tx),
            })
        return hits

# ----- FAISS + embeddings -----
class FaissRetriever(BaseRetriever):
    def __init__(self, root: Path, index_path: Path, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        import faiss, numpy as np  # noqa
        from sentence_transformers import SentenceTransformer  # noqa

        self.root = root
        self.index_path = index_path
        self.model = SentenceTransformer(model_name)

        # load index + metadata
        self.index = faiss.read_index(str(index_path / "lore.index"))
        self.paths = (index_path / "paths.txt").read_text(encoding="utf-8").splitlines()

    @staticmethod
    def _first(text: str, n=200):
        for ln in text.splitlines():
            ln = ln.strip()
            if ln: return (ln[:n-3]+"...") if len(ln)>n else ln
        return text[:n]

    @staticmethod
    def _nice_title(path: Path, text: str) -> str:
        for ln in text.splitlines():
            if ln.strip().startswith("#"):
                return re.sub(r"^#+\\s*", "", ln).strip()
        return path.stem.replace("_"," ").replace("-"," ").strip() or path.name

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        import faiss, numpy as np
        qv = self.model.encode([query], normalize_embeddings=True)
        D, I = self.index.search(qv.astype("float32"), top_k)
        hits: List[Dict[str, Any]] = []
        for d, i in zip(D[0], I[0]):
            if i < 0: continue
            p = Path(self.paths[i])
            try:
                tx = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                tx = ""
            hits.append({
                "title": self._nice_title(p, tx),
                "path": str(p),
                "score": float(d),
                "snippet": self._first(tx),
            })
        return hits

def make_retriever(kind: str, repo_root: Path) -> BaseRetriever:
    lore = repo_root / "lore-scrolls"
    if kind == "faiss":
        idx = repo_root / "data" / "faiss_index"
        return FaissRetriever(lore, idx)
    return LocalRetriever(lore)

#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
import argparse, re, json

def tokenize(s: str): return re.findall(r"[A-Za-z0-9_#@]+", s.lower())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lore", default="lore-scrolls", help="path to lore-scrolls root")
    ap.add_argument("--out", default="data/faiss_index", help="output dir for index")
    ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = ap.parse_args()

    lore = Path(args.lore).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # collect files
    exts = {".md", ".markdown", ".txt"}
    paths = sorted(p for p in lore.rglob("*") if p.is_file() and p.suffix.lower() in exts)
    if not paths:
        print("No lore-scrolls found.")
        return

    from sentence_transformers import SentenceTransformer
    import numpy as np, faiss

    model = SentenceTransformer(args.model)
    texts = []
    for p in paths:
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            t = ""
        texts.append(t)

    embs = model.encode(texts, normalize_embeddings=True)  # (N, d) float32
    embs = embs.astype("float32")
    d = embs.shape[1]
    index = faiss.IndexFlatIP(d)  # cosine via normalized vectors
    index.add(embs)

    faiss.write_index(index, str(out / "lore.index"))
    (out / "paths.txt").write_text("\n".join(str(p) for p in paths), encoding="utf-8")
    meta = {"count": len(paths), "model": args.model}
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote index for {len(paths)} docs to {out}")

if __name__ == "__main__":
    main()

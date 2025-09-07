#!/usr/bin/env python3
import argparse, json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def read_text(p: Path) -> str:
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        t = ""
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Dir of scrolls")
    ap.add_argument("--out", required=True, help="Index dir (will be created)")
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    args = ap.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted([p for p in in_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".txt"}])
    if not files:
        print(f"[indexer] no .md/.txt files in {in_dir}")
        return

    print(f"[indexer] loading model: {args.model}")
    model = SentenceTransformer(args.model)

    texts = [read_text(p) for p in files]
    print(f"[indexer] embedding {len(files)} files …")
    embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    dim = embs.shape[1]

    index = faiss.IndexFlatIP(dim)  # cosine via normalized vectors
    index.add(embs.astype("float32"))

    faiss.write_index(index, str(out_dir / "vectors.faiss"))
    (meta_path := out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    np.save(out_dir / "embeddings.npy", embs.astype("float32"))

    print(f"[indexer] wrote {out_dir}/vectors.faiss and meta.json")

if __name__ == "__main__":
    main()

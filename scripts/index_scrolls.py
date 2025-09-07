#!/usr/bin/env python3
import argparse, json, os, re, sys
from pathlib import Path
from typing import List, Dict, Any

import numpy as np

try:
    import faiss  # type: ignore
    _HAS_FAISS = True
except Exception:
    _HAS_FAISS = False

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    print("ERROR: sentence-transformers is required:", e, file=sys.stderr)
    sys.exit(1)

YAML_FM = re.compile(r"(?s)^---\n.*?\n---\s*")

def read_markdown_chunks(p: Path, max_len=800):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    txt = YAML_FM.sub("", txt).strip()
    # naive: split on blank lines; join short lines
    paras = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"\n\s*\n", txt) if x.strip()]
    # simple re-chunk by length
    chunks, cur = [], ""
    for para in paras:
        if len(cur) + 1 + len(para) <= max_len:
            cur = f"{cur}\n{para}".strip()
        else:
            if cur: chunks.append(cur)
            cur = para
    if cur: chunks.append(cur)
    return chunks

def build_index(scrolls_dir: Path, out_dir: Path, model_name: str, normalize=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in scrolls_dir.rglob("*.md") if p.is_file()])
    if not files:
        print(f"WARNING: no markdown in {scrolls_dir}", file=sys.stderr)

    model = SentenceTransformer(model_name)

    texts, metas = [], []
    for f in files:
        for i, chunk in enumerate(read_markdown_chunks(f)):
            if len(chunk) < 20:  # skip trivial
                continue
            texts.append(chunk)
            metas.append({"path": str(f), "chunk": i})

    if not texts:
        print("No chunks produced.", file=sys.stderr)
        return

    print(f"Encoding {len(texts)} chunks with {model_name}...")
    embs = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    if normalize:
        # cosine via inner product on L2-normalized vectors
        norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-12
        embs = embs / norms

    np.save(out_dir / "embeddings.npy", embs)
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump({"items": metas, "model": model_name, "normalize": normalize}, f, indent=2)

    if _HAS_FAISS:
        index = faiss.IndexFlatIP(embs.shape[1])
        index.add(embs.astype(np.float32))
        faiss.write_index(index, str(out_dir / "vectors.faiss"))
        print(f"Wrote FAISS index with {index.ntotal} vectors.")
    else:
        print("FAISS not available; falling back to NumPy-only search.")

    print(f"OK: {out_dir}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrolls", default=os.environ.get("TW_SCROLLS_DIR", "lore-scrolls"))
    ap.add_argument("--out", default="data/index")
    ap.add_argument("--model", default=os.environ.get("TW_EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    args = ap.parse_args()
    build_index(Path(args.scrolls), Path(args.out), args.model)

if __name__ == "__main__":
    main()

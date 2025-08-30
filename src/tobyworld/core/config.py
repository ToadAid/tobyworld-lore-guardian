from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    # App info
    app_name: str = "Tobyworld Mirror V3"
    version: str = "v3.0"
    debug: bool = False

    # Paths (overridable via TW_DATA_DIR / TW_SCROLLS_DIR)
    data_dir: Path = Path("data")
    scrolls_dir: Path = Path("lore-scrolls")

    # Retrieval / RAG defaults (MirrorCore expects these)
    rag_top_k: int = 5                        # TW_RAG_TOP_K
    rag_min_score: float = 0.0                # TW_RAG_MIN_SCORE
    embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"  # TW_EMBED_MODEL_NAME
    faiss_index_path: Path = Path("data/index/faiss.idx")             # TW_FAISS_INDEX_PATH
    faiss_meta_path: Path = Path("data/index/meta.json")              # TW_FAISS_META_PATH

    # Resonance/decay used by MirrorCore
    decay_half_life_days: float = 14.0        # TW_DECAY_HALF_LIFE_DAYS

    # Optional server bind (usually set by your launcher, not critical here)
    host: str = "0.0.0.0"                     # TW_HOST
    port: int = 8080                          # TW_PORT

    model_config = SettingsConfigDict(
        env_file=".env",       # env overrides supported
        env_prefix="TW_",      # e.g., TW_RAG_TOP_K, TW_DATA_DIR, ...
        extra="ignore",        # ignore unrelated env keys
        case_sensitive=False,
    )

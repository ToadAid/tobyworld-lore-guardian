# src/tobyworld/core/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    # App
    app_name: str = "Tobyworld Mirror V3"
    version: str = "v3.0"
    debug: bool = False

    # Paths
    data_dir: Path = Path("data")
    scrolls_dir: Path = Path("lore-scrolls")

    # Retrieval / RAG
    embedding_model: str = "all-MiniLM-L6-v2"  # env: TW_EMBEDDING_MODEL
    rag_top_k: int = 5                         # env: TW_RAG_TOP_K

    # Traits
    decay_half_life_days: float = 14.0         # env: TW_DECAY_HALF_LIFE_DAYS

    # Optional server knobs (not strictly used by app when started via uvicorn flags)
    host: str = "0.0.0.0"
    port: int = 8080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TW_",     # TW_DATA_DIR, TW_SCROLLS_DIR, TW_EMBEDDING_MODEL, TW_RAG_TOP_K, ...
        extra="ignore",       # ignore unrelated env vars
        case_sensitive=False,
    )

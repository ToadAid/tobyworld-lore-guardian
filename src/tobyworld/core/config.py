from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    env: str = "dev"
    version: str = "v3.0"
    data_dir: str = "data"
    index_path: str = "data/index/faiss.idx"
    rag_top_k: int = 6
    decay_half_life_days: float = 7.0

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MIRROR_")

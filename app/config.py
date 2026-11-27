
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Production RAG Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    QDRANT_PATH: str = "data/qdrant"
    QDRANT_COLLECTION: str = "documents"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

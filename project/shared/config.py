"""
Projedeki servislerin .env üzerinden ortak ayarlarını okumak için kullanılır.

Orchestration_service, matching_service, rag_service ve ingestion_service
aynı ortam değişkenlerini farklı yerlerde kullanacak. URL, port, Qdrant, LLM ayarlarını
her serviste ayrı ayrı yazmak yerine buradan yönetiyoruz.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Genel proje ayarları
    PROJECT_NAME: str = "tesvik-destek"
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Servis URL'leri
    ORCHESTRATION_SERVICE_URL: str = Field(default="http://orchestration_service:8000")
    MATCHING_SERVICE_URL: str = Field(default="http://matching_service:8001")
    RAG_SERVICE_URL: str = Field(default="http://rag_service:8002")

    # Qdrant ayarları
    QDRANT_URL: str = Field(default="http://qdrant:6333")
    QDRANT_COLLECTION_NAME: str = Field(default="tesvik_program_chunks")

    # Embedding ayarları
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # LLM ayarları
    LLM_PROVIDER: str = Field(default="openai")
    LLM_MODEL_NAME: str = Field(default="gpt-4o-mini")
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # RAG ayarları
    DEFAULT_TOP_K: int = Field(default=5, ge=1, le=20)
    DEFAULT_TOP_K_CHUNKS: int = Field(default=5, ge=1, le=20)
    MIN_RETRIEVAL_SCORE: float = Field(default=0.30, ge=0, le=1)

    # API timeout
    SERVICE_TIMEOUT_SECONDS: int = Field(default=30, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
"""Application configuration helpers."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    app_name: str = Field(default="Logiq")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOGIQ_LOG_LEVEL")

    database_url: str = Field(alias="DATABASE_URL")
    celery_broker_url: str = Field(
        default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://redis:6379/0", alias="CELERY_RESULT_BACKEND")

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_NAME"
    )
    llm_model_path: Optional[str] = Field(default=None, alias="LLM_MODEL_PATH")
    llm_n_ctx: int = Field(default=4096, alias="LLM_N_CTX")
    llm_n_threads: int = Field(default=0, alias="LLM_N_THREADS")
    llm_n_gpu_layers: int = Field(default=0, alias="LLM_N_GPU_LAYERS")
    llm_batch_size: int = Field(default=512, alias="LLM_BATCH_SIZE")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_top_p: float = Field(default=0.9, alias="LLM_TOP_P")

    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")
    max_context_logs: int = Field(default=10, alias="MAX_CONTEXT_LOGS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def model_post_init(self, __context: object) -> None:
        """Normalize any dependent settings after load."""

        if not self.celery_result_backend:
            object.__setattr__(self, "celery_result_backend",
                               self.celery_broker_url)


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of runtime settings."""
    return Settings()

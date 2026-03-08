"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration – every value comes from env vars or .env file."""

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://kembang:kembang@localhost:5432/kembang_db"

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT Auth ──────────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    # ── LLM Providers ────────────────────────────────────────────────────────
    # LiteLLM will automatically pick these up if present in the environment
    OPENAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    # ── LLM Models ────────────────────────────────────────────────────────
    # To use Groq, prefix with "groq/"
    DEFAULT_LLM_MODEL: str = "groq/llama-3.1-8b-instant"
    FALLBACK_LLM_MODEL: str = "groq/llama-3.1-8b-instant"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── App ────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── RAG tuning ────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 80
    MAX_CONTEXT_TOKENS: int = 1500
    HISTORY_LIMIT: int = 6
    VECTOR_TOP_K: int = 8
    KEYWORD_TOP_K: int = 8
    RERANK_TOP_K: int = 4

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

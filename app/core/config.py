"""Application settings loaded from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration – every value comes from env vars or .env file."""

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://kembang:kembang@localhost:5432/kembang_db"

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str | None = None  # Upstash Redis URL (optional for rate limiting)

    # ── JWT Auth ──────────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is strong enough."""
        if not v or v == "change-me":
            raise ValueError(
                "JWT_SECRET must be set to a secure random string (min 32 characters). "
                "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if len(v) < 32:
            raise ValueError(
                f"JWT_SECRET must be at least 32 characters long (got {len(v)}). "
                "Use a secure random string for production."
            )
        return v

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
    APP_ENV: str = "production"  # Changed from development
    DEBUG: bool = False  # Changed to False for production
    CORS_ORIGINS: str | list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "https://kembang-tenant.vercel.app",  # Tenant Dashboard
        "https://kembang-console.vercel.app",  # Superadmin Console
        "https://*.hf.space",  # Allow all Hugging Face Spaces
        "https://huggingface.co",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
            else:
                import json
                return json.loads(v)
        return v

    # ── RAG tuning ────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 80
    MAX_CONTEXT_TOKENS: int = 600  # Reduced from 1500 for cost optimization
    HISTORY_LIMIT: int = 3  # Reduced from 6 for cost optimization
    VECTOR_TOP_K: int = 8
    KEYWORD_TOP_K: int = 8
    RERANK_TOP_K: int = 4
    
    # ── Cache configuration ───────────────────────────────────────────────
    RESPONSE_CACHE_TTL: int = 7200  # 2 hours
    RESPONSE_CACHE_MAXSIZE: int = 1000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

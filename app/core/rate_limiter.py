"""Rate limiter configuration for security."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings


# Create limiter instance
# Use Redis if available (production), otherwise memory (development)
storage_uri = settings.REDIS_URL if settings.REDIS_URL else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default limit for all endpoints
    storage_uri=storage_uri
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "rate_limit_exceeded",
            "message": f"Too many requests. Please try again after {exc.detail}",
            "retry_after": str(exc.detail),
        },
    )


# Security-focused rate limits for different endpoints
AUTH_LIMIT = "5/minute"  # Login/register: max 5 per minute
CHAT_LIMIT = "30/minute"  # Chat: max 30 per minute
UPLOAD_LIMIT = "10/hour"  # File upload: max 10 per hour
ADMIN_LIMIT = "20/minute"  # Admin endpoints: max 20 per minute

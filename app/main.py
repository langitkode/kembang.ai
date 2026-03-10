"""FastAPI application entry point."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.routes_admin import router as admin_router
from app.api.routes_api_keys import router as api_keys_router
from app.api.routes_auth import router as auth_router
from app.api.routes_chat import router as chat_router
from app.api.routes_faq import router as faq_router
from app.api.routes_kb import router as kb_router
from app.api.routes_omnichannel import router as omnichannel_router
from app.api.routes_products import router as products_router
from app.api.routes_superadmin import router as superadmin_router
from app.api.routes_widget import router as widget_router
from app.core.config import settings
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.db.session import engine, async_session_factory
from app.monitoring.metrics import metrics
from sqlalchemy import select

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("Starting Kembang AI backend (env=%s)", settings.APP_ENV)
    logger.info("CORS Origins: %s", settings.CORS_ORIGINS)

    # Startup validation
    try:
        # Check database connection
        async with async_session_factory() as db:
            await db.execute(select(1))
            logger.info("✅ Database connection OK")

        # Pre-load embedding model to avoid cold start and permission issues
        logger.info("Pre-loading embedding model...")
        from app.services.embedding_service import get_model
        get_model()  # This will cache the model
        logger.info("✅ Embedding model loaded")

        # Check if migrations are up to date
        logger.info("✅ Backend ready to serve requests")
    except Exception as e:
        logger.error("❌ Startup validation failed: %s", e)
        raise

    yield

    # Shutdown
    await engine.dispose()
    logger.info("Kembang AI backend shut down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Kembang AI",
    description="Agency-first AI chatbot SaaS for UMKM customer service",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log request info and record metrics."""
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000

    metrics.record_request(
        endpoint=request.url.path,
        latency_ms=latency_ms,
        error=response.status_code >= 400,
    )

    logger.info(
        "%s %s → %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response


# ── Security Headers Middleware ───────────────────────────────────────────────


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # HSTS (only in production)
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(kb_router, prefix="/api/v1")
app.include_router(faq_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1/superadmin")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(widget_router, prefix="/api/v1")
app.include_router(superadmin_router, prefix="/api/v1")
app.include_router(omnichannel_router, prefix="/api/v1/omnichannel", tags=["Omnichannel"])


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "ok"}


@app.get("/metrics")
async def get_metrics():
    """Return in-memory request metrics."""
    return metrics.summary()

"""Usage logger – async helper for recording LLM call metadata."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)


async def log_llm_usage(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Convenience function to log LLM usage from anywhere in the codebase.

    Wraps ``UsageService.log_usage`` with error handling so a logging
    failure never crashes the main request.
    """
    try:
        svc = UsageService(db)
        await svc.log_usage(
            tenant_id=tenant_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception:
        logger.exception("Failed to log LLM usage for tenant %s", tenant_id)

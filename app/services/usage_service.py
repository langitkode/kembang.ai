"""Usage service – track token usage and cost per tenant."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog


# Rough per-1k-token pricing (USD).  Update as models change.
_COST_MAP: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
}


class UsageService:
    """Records and queries LLM usage per tenant."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Write ─────────────────────────────────────────────────────────────

    async def log_usage(
        self,
        tenant_id: uuid.UUID,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> UsageLog:
        """Persist a single usage record with cost estimate."""
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        log = UsageLog(
            tenant_id=tenant_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_estimate=cost,
        )
        self._db.add(log)
        await self._db.commit()
        await self._db.refresh(log)
        return log

    # ── Read ──────────────────────────────────────────────────────────────

    async def tenant_usage_summary(self, tenant_id: uuid.UUID) -> dict:
        """Aggregate usage stats for a tenant.

        Returns::

            {
                "requests": 120,
                "total_input_tokens": 45000,
                "total_output_tokens": 12000,
                "estimated_cost": 1.23,
            }
        """
        result = await self._db.execute(
            select(
                func.count(UsageLog.id).label("requests"),
                func.coalesce(func.sum(UsageLog.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(UsageLog.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(UsageLog.cost_estimate), 0.0).label("cost"),
            ).where(UsageLog.tenant_id == tenant_id)
        )
        row = result.one()
        return {
            "requests": row.requests,
            "total_input_tokens": row.input_tokens,
            "total_output_tokens": row.output_tokens,
            "estimated_cost": round(row.cost, 4),
        }

    # ── Cost estimation ───────────────────────────────────────────────────

    @staticmethod
    def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate USD cost based on known per-1k-token prices."""
        prices = _COST_MAP.get(model, {"input": 0.0, "output": 0.0})
        return (
            (input_tokens / 1000) * prices["input"]
            + (output_tokens / 1000) * prices["output"]
        )

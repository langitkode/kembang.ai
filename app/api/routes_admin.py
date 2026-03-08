"""Admin routes – usage monitoring and tenant management."""

import secrets

from fastapi import APIRouter
from sqlalchemy import select

from app.api.schemas import UsageSummaryResponse
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.services.usage_service import UsageService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/generate-api-key")
async def generate_api_key(db: DBSession, user: CurrentUser, tenant: CurrentTenant):
    """Generate or rotate the API Key for the current tenant's widget."""
    new_key = f"sk_live_{secrets.token_urlsafe(24)}"
    tenant.api_key = new_key
    await db.commit()
    
    return {"api_key": new_key, "message": "API Key generated successfully. Keep it secret!"}


@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Return aggregated usage statistics for the current tenant."""
    usage_svc = UsageService(db)
    summary = await usage_svc.tenant_usage_summary(tenant.id)
    return UsageSummaryResponse(**summary)

"""API Key Management routes – Superadmin monitoring."""

import logging
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, update

from app.core.dependencies import CurrentUser, DBSession
from app.core.dependencies import require_superadmin
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys", "superadmin"])


# ── Response Schemas ──────────────────────────────────────────────────────────


class APIKeyOut(BaseModel):
    """API Key output schema."""
    id: str
    tenant_id: str
    tenant_name: str
    key_masked: str
    created_at: str
    is_active: bool
    last_used_at: Optional[str] = None


class APIKeyListResponse(BaseModel):
    """API Key list response."""
    api_keys: list[APIKeyOut]
    total: int
    page: int
    page_size: int


class APIKeyRevokeResponse(BaseModel):
    """API Key revoke response."""
    success: bool
    message: str
    revoked_at: str


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    db: DBSession,
    user: CurrentUser = require_superadmin,
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List all API keys across all tenants.
    
    Requires superadmin access.
    """
    # Build query
    query = select(Tenant).where(Tenant.api_key.isnot(None))
    
    if tenant_id:
        query = query.where(Tenant.id == tenant_id)
    
    # Get total count
    count_query = select(func.count(Tenant.id)).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    # Convert to API key format
    api_keys = []
    for tenant in tenants:
        api_keys.append(
            APIKeyOut(
                id=str(tenant.id),  # Using tenant ID as key ID
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                key_masked=f"kw_...{tenant.api_key[-4:]}" if tenant.api_key else None,
                created_at=tenant.created_at.isoformat() if tenant.created_at else None,
                is_active=True,  # All tenants are active by default
                last_used_at=None  # Track last usage in future enhancement
            )
        )
    
    return APIKeyListResponse(
        api_keys=api_keys,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/{tenant_id}/revoke", response_model=APIKeyRevokeResponse)
async def revoke_api_key(
    tenant_id: UUID,
    db: DBSession,
    user: CurrentUser = require_superadmin,
):
    """Revoke API key for a specific tenant.
    
    This will generate a new random API key, effectively revoking the old one.
    
    Requires superadmin access.
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tenant_not_found",
        )
    
    if not tenant.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_has_no_api_key",
        )
    
    # Store old key for logging
    old_key = tenant.api_key
    
    # Generate new API key (effectively revokes old one)
    new_key = f"kw_{secrets.token_urlsafe(24)}"
    tenant.api_key = new_key
    
    await db.commit()
    
    logger.info(
        "Superadmin %s revoked API key for tenant %s (%s)",
        user.email,
        tenant.name,
        tenant_id
    )
    
    return APIKeyRevokeResponse(
        success=True,
        message=f"API key revoked for tenant '{tenant.name}'. New key generated.",
        revoked_at=datetime.now().isoformat()
    )


@router.post("/{tenant_id}/regenerate", response_model=APIKeyRevokeResponse)
async def regenerate_api_key(
    tenant_id: UUID,
    db: DBSession,
    user: CurrentUser = require_superadmin,
):
    """Regenerate API key for a tenant.
    
    Similar to revoke, but explicitly for regeneration use case.
    
    Requires superadmin access.
    """
    # Get tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tenant_not_found",
        )
    
    # Generate new API key
    new_key = f"kw_{secrets.token_urlsafe(24)}"
    old_key = tenant.api_key
    tenant.api_key = new_key
    
    await db.commit()
    
    logger.info(
        "Superadmin %s regenerated API key for tenant %s (%s)",
        user.email,
        tenant.name,
        tenant_id
    )
    
    return APIKeyRevokeResponse(
        success=True,
        message=f"API key regenerated for tenant '{tenant.name}'.",
        revoked_at=datetime.now().isoformat()
    )

"""Admin routes – usage monitoring and tenant management."""

import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.schemas import (
    UsageSummaryResponse,
    UserCreate,
    UserUpdate,
    UserListResponse,
    UserOut,
)
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.core.security import hash_password
from app.models.user import User
from app.services.usage_service import UsageService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def list_team_users(db: DBSession, user: CurrentUser, tenant: CurrentTenant):
    """List all users in the current tenant."""
    result = await db.execute(
        select(User).where(User.tenant_id == tenant.id).order_by(User.email)
    )
    users = result.scalars().all()
    return UserListResponse(users=users)


@router.post("/users", response_model=UserOut, status_code=201)
async def create_team_user(
    body: UserCreate, db: DBSession, user: CurrentUser, tenant: CurrentTenant
):
    """Add a new user to the tenant team."""
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="user_already_exists")

    new_user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.delete("/users/{user_id}", status_code=204)
async def delete_team_user(
    user_id: UUID, db: DBSession, user: CurrentUser, tenant: CurrentTenant
):
    """Remove a user from the tenant team."""
    result = await db.execute(
        select(User).where(User.id == user_id).where(User.tenant_id == tenant.id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="user_not_found")

    if target_user.id == user.id:
        raise HTTPException(status_code=400, detail="cannot_delete_self")

    await db.delete(target_user)
    await db.commit()
    return None


@router.get("/api-key")
async def get_api_key(db: DBSession, user: CurrentUser, tenant: CurrentTenant):
    """Retrieve the current API Key for the tenant's widget."""
    return {"api_key": tenant.api_key}

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
    date_from: Optional[datetime] = Query(None, description="Filter from date (inclusive)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (inclusive)"),
):
    """Return aggregated usage statistics for the current tenant.
    
    Supports optional date range filtering.
    
    - **date_from**: Filter usage from this date (e.g., 2026-03-01)
    - **date_to**: Filter usage until this date (e.g., 2026-03-09)
    
    If no dates provided, returns ALL historical data.
    """
    usage_svc = UsageService(db)
    summary = await usage_svc.tenant_usage_summary(
        tenant_id=tenant.id,
        date_from=date_from,
        date_to=date_to
    )
    return UsageSummaryResponse(**summary)

"""Superadmin routes – platform-level management across ALL tenants.

These endpoints are restricted to users with ``role="superadmin"``.
They provide cross-tenant visibility for the Developer Console.
"""

import logging
import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, or_

logger = logging.getLogger(__name__)

from app.api.schemas import (
    CreateTenantRequest,
    ConversationListResponse,
    ConversationOut,
    HistoryResponse,
    MessageOut,
    PlatformStatsResponse,
    TenantListResponse,
    TenantOut,
    TokenResponse,
    UpdateTenantRequest,
    UsageSummaryResponse,
    UserCreate,
    UserUpdate,
    UserListResponse,
    UserOut,
)
from app.api.schemas_pagination import PaginationInfo
from app.core.dependencies import DBSession, SuperAdminUser
from app.core.security import create_access_token, hash_password
from app.models.conversation import Conversation
from app.models.document import Document, KnowledgeBase
from app.models.message import Message
from app.models.tenant import Tenant
from app.models.usage_log import UsageLog
from app.models.user import User

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


# ── Platform Stats ────────────────────────────────────────────────────────────


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(db: DBSession, user: SuperAdminUser):
    """Return high-level platform statistics across all tenants."""
    tenant_count = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    conv_count = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    request_count = (await db.execute(select(func.count(UsageLog.id)))).scalar() or 0
    total_cost_result = await db.execute(
        select(func.coalesce(func.sum(UsageLog.cost_estimate), 0.0))
    )
    total_cost = float(total_cost_result.scalar() or 0.0)

    return PlatformStatsResponse(
        total_tenants=tenant_count,
        total_documents=doc_count,
        total_conversations=conv_count,
        total_requests=request_count,
        total_estimated_cost=total_cost,
    )


# ── List All Tenants ──────────────────────────────────────────────────────────


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(db: DBSession, user: SuperAdminUser):
    """List ALL tenants on the platform with aggregated metrics."""
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc())
    )
    tenants = result.scalars().all()

    tenant_list = []
    for t in tenants:
        # Count users per tenant
        user_count_result = await db.execute(
            select(func.count(User.id)).where(User.tenant_id == t.id)
        )
        user_count = user_count_result.scalar() or 0

        # Count documents per tenant
        doc_count_result = await db.execute(
            select(func.count(Document.id))
            .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
            .where(KnowledgeBase.tenant_id == t.id)
        )
        doc_count = doc_count_result.scalar() or 0

        tenant_list.append(
            TenantOut(
                id=str(t.id),
                name=t.name,
                plan=t.plan or "free",
                api_key_masked=f"sk_...{t.api_key[-4:]}" if t.api_key else None,
                user_count=user_count,
                doc_count=doc_count,
                created_at=t.created_at.isoformat() if t.created_at else None,
            )
        )

    return TenantListResponse(tenants=tenant_list)


# ── Create Tenant ─────────────────────────────────────────────────────────────


@router.post("/tenants", response_model=TenantOut, status_code=201)
async def create_tenant(
    body: CreateTenantRequest, db: DBSession, user: SuperAdminUser
):
    """Create a new tenant with its first admin user."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == body.admin_email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email_already_registered",
        )

    tenant = Tenant(name=body.name)
    db.add(tenant)
    await db.flush()

    admin_user = User(
        tenant_id=tenant.id,
        email=body.admin_email,
        password_hash=hash_password(body.admin_password),
        role="admin",
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(tenant)

    return TenantOut(
        id=str(tenant.id),
        name=tenant.name,
        plan=tenant.plan or "free",
        api_key_masked=None,
        user_count=1,
        doc_count=0,
        created_at=tenant.created_at.isoformat() if tenant.created_at else None,
    )


# ── Single Tenant Detail ─────────────────────────────────────────────────────


@router.get("/tenants/{tenant_id}")
async def get_tenant_detail(
    tenant_id: str, db: DBSession, user: SuperAdminUser
):
    """Get detailed info for a single tenant."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == UUID(tenant_id))
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tenant_not_found",
        )

    user_count = (
        await db.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant.id)
        )
    ).scalar() or 0

    doc_count = (
        await db.execute(
            select(func.count(Document.id))
            .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
            .where(KnowledgeBase.tenant_id == tenant.id)
        )
    ).scalar() or 0

    return TenantOut(
        id=str(tenant.id),
        name=tenant.name,
        plan=tenant.plan or "free",
        api_key_masked=f"sk_...{tenant.api_key[-4:]}" if tenant.api_key else None,
        user_count=user_count,
        doc_count=doc_count,
        created_at=tenant.created_at.isoformat() if tenant.created_at else None,
    )


# ── Global Usage ──────────────────────────────────────────────────────────────


@router.get("/usage", response_model=UsageSummaryResponse)
async def global_usage(db: DBSession, user: SuperAdminUser):
    """Return aggregated usage statistics across ALL tenants."""
    result = await db.execute(
        select(
            func.count(UsageLog.id).label("requests"),
            func.coalesce(func.sum(UsageLog.input_tokens), 0).label("input"),
            func.coalesce(func.sum(UsageLog.output_tokens), 0).label("output"),
            func.coalesce(func.sum(UsageLog.cost_estimate), 0.0).label("cost"),
        )
    )
    row = result.one()
    return UsageSummaryResponse(
        requests=row.requests,
        total_input_tokens=int(row.input),
        total_output_tokens=int(row.output),
        estimated_cost=float(row.cost),
    )


# ── Global Conversations ─────────────────────────────────────────────────────


@router.get("/conversations", response_model=ConversationListResponse)
async def global_conversations(db: DBSession, user: SuperAdminUser):
    """List recent conversations across ALL tenants (most recent first).
    
    DEPRECATED: Use /conversations/paginated instead for better performance.
    This endpoint returns only last 100 conversations.
    """
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(100)
    )
    conversations = result.scalars().all()

    return ConversationListResponse(
        conversations=[
            ConversationOut(
                id=str(c.id),
                user_identifier=c.user_identifier,
                created_at=c.created_at.isoformat() if c.created_at else None,
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
                summary=c.summary,
            )
            for c in conversations
        ]
    )


@router.get("/conversations/paginated")
async def list_conversations_paginated(
    db: DBSession,
    user: SuperAdminUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    search: Optional[str] = Query(None, description="Search user_identifier or summary"),
):
    """List conversations across ALL tenants with pagination and filters.
    
    - **page**: Page number (starts from 1)
    - **page_size**: Items per page (1-100, default: 50)
    - **tenant_id**: Optional filter by specific tenant
    - **date_from**: Optional filter from date (YYYY-MM-DD)
    - **date_to**: Optional filter to date (YYYY-MM-DD)
    - **search**: Optional search in user_identifier or summary
    
    Returns conversations ordered by updated_at DESC (newest first).
    """
    # Build base query
    query = select(Conversation)
    
    # Apply filters
    if tenant_id:
        query = query.where(Conversation.tenant_id == tenant_id)
    if date_from:
        query = query.where(Conversation.updated_at >= date_from)
    if date_to:
        query = query.where(Conversation.updated_at <= date_to)
    if search:
        query = query.where(
            or_(
                Conversation.user_identifier.ilike(f"%{search}%"),
                Conversation.summary.ilike(f"%{search}%")
            )
        )
    
    # Get total count BEFORE pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Calculate pagination
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return {
        "conversations": [
            {
                "id": str(c.id),
                "user_identifier": c.user_identifier,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "summary": c.summary,
            }
            for c in conversations
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
    }


# ── Global Conversation History ──────────────────────────────────────────────


@router.get("/conversations/{conversation_id}", response_model=HistoryResponse)
async def global_conversation_history(
    conversation_id: UUID, db: DBSession, user: SuperAdminUser
):
    """Retrieve all messages for a specific conversation across the platform."""
    # Verify the conversation exists
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation_not_found",
        )

    # Get all messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return HistoryResponse(
        messages=[MessageOut(role=m.role, content=m.content) for m in messages]
    )


# ── Update Tenant ─────────────────────────────────────────────────────────────


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: UUID,
    body: UpdateTenantRequest,
    db: DBSession,
    user: SuperAdminUser,
):
    """Update tenant metadata like name or subscription plan."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tenant_not_found",
        )

    if body.name is not None:
        tenant.name = body.name
    if body.plan is not None:
        tenant.plan = body.plan

    await db.commit()
    await db.refresh(tenant)

    # Re-calculate usage stats for the response
    user_count = (
        await db.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant.id)
        )
    ).scalar() or 0
    doc_count = (
        await db.execute(
            select(func.count(Document.id))
            .join(KnowledgeBase, KnowledgeBase.id == Document.kb_id)
            .where(KnowledgeBase.tenant_id == tenant.id)
        )
    ).scalar() or 0

    return TenantOut(
        id=str(tenant.id),
        name=tenant.name,
        plan=tenant.plan or "free",
        api_key_masked=f"sk_...{tenant.api_key[-4:]}" if tenant.api_key else None,
        user_count=user_count,
        doc_count=doc_count,
        created_at=tenant.created_at.isoformat() if tenant.created_at else None,
    )


# ── Delete Tenant ─────────────────────────────────────────────────────────────


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID, db: DBSession, user: SuperAdminUser
):
    """Permanently delete a tenant and ALL associated data."""
    logger.info("DELETE tenant request for ID: %s", tenant_id)
    try:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            logger.warning("Tenant not found: %s", tenant_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="tenant_not_found",
            )

        # Safety check: Do not delete the platform tenant
        if tenant.name in ["Kembang Platform", "Platform"]:
            logger.warning("Attempted to delete platform tenant: %s", tenant_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cannot_delete_platform_tenant",
            )

        # We bypass ORM-level db.delete() to avoid SQLAlchemy's "orphan protection"
        # which triggers illegal UPDATE SET tenant_id=NULL on children.
        # DB-level ON DELETE CASCADE handles all cleanup atomically.
        from sqlalchemy import delete
        
        # IMPORTANT: Expunge the object from the session so SQLAlchemy 
        # stops trying to manage its child relationships during commit.
        db.expunge(tenant)
        
        await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
        
        await db.commit()
        logger.info("Transaction committed successfully for tenant: %s", tenant_id)
        return None
    except Exception as e:
        logger.exception("Error during tenant deletion: %s", str(e))
        raise


# ── User Management ───────────────────────────────────────────────────────────


@router.get("/users", response_model=UserListResponse)
async def list_users(db: DBSession, user: SuperAdminUser):
    """List all users across all tenants."""
    result = await db.execute(select(User).order_by(User.email))
    users = result.scalars().all()
    return UserListResponse(users=users)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: DBSession, super_user: SuperAdminUser):
    """Create a new user (admin or superadmin)."""
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user_already_exists",
        )

    # Validate tenant if not superadmin
    if body.role != "superadmin" and not body.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id_required_for_non_superadmin",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        tenant_id=body.tenant_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID, body: UserUpdate, db: DBSession, super_user: SuperAdminUser
):
    """Update user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found"
        )

    if body.email is not None:
        user.email = body.email
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.role is not None:
        user.role = body.role

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, db: DBSession, super_user: SuperAdminUser):
    """Delete a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found"
        )

    # Don't delete yourself? (Optional safety check)
    await db.delete(user)
    await db.commit()
    return None

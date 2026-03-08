"""Superadmin routes – platform-level management across ALL tenants.

These endpoints are restricted to users with ``role="superadmin"``.
They provide cross-tenant visibility for the Developer Console.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.schemas import (
    CreateTenantRequest,
    ConversationListResponse,
    ConversationOut,
    PlatformStatsResponse,
    TenantListResponse,
    TenantOut,
    TokenResponse,
    UsageSummaryResponse,
)
from app.core.dependencies import DBSession, SuperAdminUser
from app.core.security import create_access_token, hash_password
from app.models.conversation import Conversation
from app.models.document import Document, KnowledgeBase
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
    """List recent conversations across ALL tenants (most recent first)."""
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

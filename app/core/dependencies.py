"""FastAPI dependency functions shared across routes.

Provides:
- ``get_db``           – async database session
- ``get_current_user`` – JWT-authenticated user
- ``get_tenant``       – validated tenant context
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.session import async_session_factory
from app.models.tenant import Tenant
from app.models.user import User

# ── Database session ──────────────────────────────────────────────────────────

_bearer = HTTPBearer()


async def get_db():
    """Yield an ``AsyncSession`` and ensure it is closed after the request."""
    async with async_session_factory() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Auth ──────────────────────────────────────────────────────────────────────


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: DBSession,
) -> User:
    """Decode JWT, look up the user, and return it.

    Raises 401 if the token is invalid or the user does not exist.
    """
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_or_expired_token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token_payload",
        )

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user_not_found",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Superadmin guard ──────────────────────────────────────────────────────────


async def require_superadmin(user: CurrentUser) -> User:
    """Ensure the current user has the ``superadmin`` role.

    Raises 403 if the user is not a platform-level superadmin.
    """
    if user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="superadmin_required",
        )
    return user


SuperAdminUser = Annotated[User, Depends(require_superadmin)]


# ── Tenant ────────────────────────────────────────────────────────────────────


async def get_tenant(
    user: CurrentUser,
    db: DBSession,
    x_tenant_id: Annotated[str | None, Header()] = None,
) -> Tenant:
    """Resolve and validate the tenant for the current request.

    For non-admin users the tenant is derived from the user record.
    Admins may override via ``X-Tenant-ID`` header.
    """
    tenant_id = UUID(x_tenant_id) if x_tenant_id else user.tenant_id

    # Ensure the user belongs to the requested tenant (or is admin).
    if user.role != "admin" and tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cross_tenant_access_denied",
        )

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tenant_not_found",
        )
    return tenant


CurrentTenant = Annotated[Tenant, Depends(get_tenant)]


async def get_tenant_from_api_key(
    db: DBSession,
    x_api_key: Annotated[str, Header()],
) -> Tenant:
    """Resolve tenant purely by widget API key (no JWT user needed)."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_api_key",
        )

    result = await db.execute(select(Tenant).where(Tenant.api_key == x_api_key))
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_api_key",
        )
    return tenant

WidgetTenant = Annotated[Tenant, Depends(get_tenant_from_api_key)]

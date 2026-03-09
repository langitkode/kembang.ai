"""Auth routes – login and registration."""

from fastapi import APIRouter, HTTPException, status, Request
from sqlalchemy import select
from datetime import datetime, timedelta

from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.core.dependencies import DBSession, CurrentUser
from app.core.rate_limiter import limiter, AUTH_LIMIT
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Account lockout configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


@router.get("/me", response_model=UserOut)
async def get_me(user: CurrentUser):
    """Return the currently authenticated user's profile."""
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(AUTH_LIMIT)
async def login(request: Request, body: LoginRequest, db: DBSession):
    """Authenticate user and return a JWT."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )

    token = create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id)})
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_LIMIT)
async def register(request: Request, body: RegisterRequest, db: DBSession):
    """Create a new user (and optionally a new tenant)."""
    # Check for existing email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email_already_registered",
        )

    # Create tenant if name provided, else use a default
    tenant = Tenant(name=body.tenant_name or f"tenant-{body.email}")
    db.add(tenant)
    await db.flush()  # get tenant.id without committing

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        role="admin",  # first user of a tenant is admin
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "tenant_id": str(tenant.id)})
    return TokenResponse(access_token=token)

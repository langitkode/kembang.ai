"""Pydantic schemas for request / response validation."""

import uuid

from pydantic import BaseModel, EmailStr, ConfigDict


# ── Auth ──────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    tenant_id: uuid.UUID
    role: str

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str | None = None


# ── Chat ──────────────────────────────────────────────────────────────────────

class ConversationOut(BaseModel):
    id: str
    user_identifier: str
    created_at: str | None = None
    updated_at: str | None = None
    summary: str | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationOut]


class ChatRequest(BaseModel):

    conversation_id: str | None = None
    message: str
    user_identifier: str = "anonymous"


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    sources: list[str] = []


class MessageOut(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    messages: list[MessageOut]


# ── Knowledge Base ────────────────────────────────────────────────────────────


class DocumentOut(BaseModel):
    id: str
    name: str
    source_type: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]


# ── Admin ─────────────────────────────────────────────────────────────────────


class UsageSummaryResponse(BaseModel):
    requests: int
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost: float


# ── Superadmin ────────────────────────────────────────────────────────────────


class TenantOut(BaseModel):
    id: str
    name: str
    plan: str
    api_key_masked: str | None = None
    user_count: int = 0
    doc_count: int = 0
    created_at: str | None = None


class TenantListResponse(BaseModel):
    tenants: list[TenantOut]


class CreateTenantRequest(BaseModel):
    name: str
    admin_email: EmailStr
    admin_password: str


class PlatformStatsResponse(BaseModel):
    total_tenants: int
    total_documents: int
    total_conversations: int
    total_requests: int
    total_estimated_cost: float

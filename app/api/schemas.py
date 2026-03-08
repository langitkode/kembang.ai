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

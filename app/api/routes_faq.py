"""FAQ Management routes – CRUD for tenant-specific FAQ."""

import uuid
import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from app.api.schemas import BaseModel
from app.core.dependencies import CurrentTenant, CurrentUser, DBSession
from app.models.faq import TenantFAQ

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faq", tags=["faq"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class FAQCreate(BaseModel):
    category: str
    question_patterns: list[str]
    answer: str
    confidence: float = 0.9
    is_active: bool = True


class FAQUpdate(BaseModel):
    category: str | None = None
    question_patterns: list[str] | None = None
    answer: str | None = None
    confidence: float | None = None
    is_active: bool | None = None


class FAQResponse(BaseModel):
    id: str
    tenant_id: str
    category: str
    question_patterns: list[str]
    answer: str
    confidence: float
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None


class FAQListResponse(BaseModel):
    faqs: list[FAQResponse]
    total: int


# ── Routes ───────────────────────────────────────────────────────────────────


@router.get("", response_model=FAQListResponse)
async def list_faqs(
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
    category: str | None = None,
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """List all FAQ for the current tenant with optional filters."""
    query = select(TenantFAQ).where(TenantFAQ.tenant_id == tenant.id)
    
    if category:
        query = query.where(TenantFAQ.category == category)
    
    if is_active is not None:
        query = query.where(TenantFAQ.is_active == is_active)
    
    # Get total count
    count_query = select(func.count(TenantFAQ.id)).where(TenantFAQ.tenant_id == tenant.id)
    if category:
        count_query = count_query.where(TenantFAQ.category == category)
    if is_active is not None:
        count_query = count_query.where(TenantFAQ.is_active == is_active)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(TenantFAQ.category, TenantFAQ.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    faqs = result.scalars().all()
    
    return FAQListResponse(
        faqs=[FAQResponse(**faq.to_dict()) for faq in faqs],
        total=total,
    )


@router.get("/{faq_id}", response_model=FAQResponse)
async def get_faq(
    faq_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Get a specific FAQ by ID."""
    result = await db.execute(
        select(TenantFAQ).where(
            TenantFAQ.id == faq_id,
            TenantFAQ.tenant_id == tenant.id
        )
    )
    faq = result.scalar_one_or_none()
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="faq_not_found",
        )
    
    return FAQResponse(**faq.to_dict())


@router.post("", response_model=FAQResponse, status_code=status.HTTP_201_CREATED)
async def create_faq(
    body: FAQCreate,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Create a new FAQ for the current tenant."""
    # Validate category
    valid_categories = [
        "business_hours", "payment", "shipping", "returns",
        "contact", "location", "pricing", "stock", "custom"
    ]
    if body.category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {valid_categories}",
        )
    
    # Validate patterns
    if not body.question_patterns or len(body.question_patterns) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one question pattern is required",
        )
    
    faq = TenantFAQ(
        tenant_id=tenant.id,
        category=body.category,
        question_patterns=body.question_patterns,
        answer=body.answer,
        confidence=body.confidence,
        is_active=body.is_active,
    )
    
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    
    logger.info("Created FAQ for tenant %s: %s", tenant.id, body.category)
    
    return FAQResponse(**faq.to_dict())


@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: uuid.UUID,
    body: FAQUpdate,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Update an existing FAQ."""
    result = await db.execute(
        select(TenantFAQ).where(
            TenantFAQ.id == faq_id,
            TenantFAQ.tenant_id == tenant.id
        )
    )
    faq = result.scalar_one_or_none()
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="faq_not_found",
        )
    
    # Update fields if provided
    if body.category is not None:
        valid_categories = [
            "business_hours", "payment", "shipping", "returns",
            "contact", "location", "pricing", "stock", "custom"
        ]
        if body.category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {valid_categories}",
            )
        faq.category = body.category
    
    if body.question_patterns is not None:
        if len(body.question_patterns) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one question pattern is required",
            )
        faq.question_patterns = body.question_patterns
    
    if body.answer is not None:
        faq.answer = body.answer
    
    if body.confidence is not None:
        faq.confidence = body.confidence
    
    if body.is_active is not None:
        faq.is_active = body.is_active
    
    await db.commit()
    await db.refresh(faq)
    
    logger.info("Updated FAQ for tenant %s: %s", tenant.id, faq_id)
    
    return FAQResponse(**faq.to_dict())


@router.delete("/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    faq_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Delete an FAQ."""
    result = await db.execute(
        select(TenantFAQ).where(
            TenantFAQ.id == faq_id,
            TenantFAQ.tenant_id == tenant.id
        )
    )
    faq = result.scalar_one_or_none()
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="faq_not_found",
        )
    
    await db.delete(faq)
    await db.commit()
    
    logger.info("Deleted FAQ for tenant %s: %s", tenant.id, faq_id)
    
    return None


@router.post("/{faq_id}/toggle", response_model=FAQResponse)
async def toggle_faq_status(
    faq_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Toggle FAQ active/inactive status."""
    result = await db.execute(
        select(TenantFAQ).where(
            TenantFAQ.id == faq_id,
            TenantFAQ.tenant_id == tenant.id
        )
    )
    faq = result.scalar_one_or_none()
    
    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="faq_not_found",
        )
    
    faq.is_active = not faq.is_active
    
    await db.commit()
    await db.refresh(faq)
    
    logger.info("Toggled FAQ status for tenant %s: %s (active=%s)", tenant.id, faq_id, faq.is_active)
    
    return FAQResponse(**faq.to_dict())


# ── Template Endpoints ───────────────────────────────────────────────────────


@router.get("/templates/categories")
async def get_faq_categories():
    """Get list of available FAQ categories with descriptions."""
    return {
        "categories": [
            {
                "id": "business_hours",
                "name": "Business Hours",
                "icon": "🕐",
                "description": "Opening hours, holidays, special hours",
                "default_patterns": ["jam buka", "buka jam berapa", "hari apa saja buka"],
                "default_answer": "Kami buka setiap hari pukul 09.00–21.00 WIB.",
            },
            {
                "id": "payment",
                "name": "Payment Methods",
                "icon": "💳",
                "description": "Payment options, e-wallets, bank transfers",
                "default_patterns": ["bayar pakai apa", "terima goPay", "transfer bca"],
                "default_answer": "Kami menerima pembayaran via E-wallet (GoPay, OVO, Dana) dan Transfer Bank (BCA, Mandiri, BNI, BRI).",
            },
            {
                "id": "shipping",
                "name": "Shipping & Delivery",
                "icon": "📦",
                "description": "Shipping options, delivery time, tracking",
                "default_patterns": ["ongkir", "berapa lama sampai", "ekspedisi apa"],
                "default_answer": "Pengiriman tersedia ke seluruh Indonesia. Jabodetabek 1-2 hari, Jawa 2-4 hari, Luar Jawa 3-7 hari.",
            },
            {
                "id": "returns",
                "name": "Returns & Refunds",
                "icon": "🔄",
                "description": "Return policy, warranty, exchanges",
                "default_patterns": ["bisa retur", "garansi berapa lama", "barang rusak"],
                "default_answer": "Retur dalam 7 hari setelah diterima. Barang harus dalam kondisi asli. Garansi resmi 1 tahun.",
            },
            {
                "id": "contact",
                "name": "Contact & Support",
                "icon": "📞",
                "description": "Customer service, WhatsApp, email",
                "default_patterns": ["hubungi cs", "nomor whatsapp", "email support"],
                "default_answer": "Hubungi kami: WhatsApp +62 812-3456-7890, Email support@company.com (09.00-21.00 WIB).",
            },
            {
                "id": "location",
                "name": "Location & Address",
                "icon": "📍",
                "description": "Store location, office address, branches",
                "default_patterns": ["alamat toko", "lokasi dimana", "cabang ada"],
                "default_answer": "Alamat kami: Jl. Raya Utama No. 123, Jakarta Selatan, 12345.",
            },
            {
                "id": "pricing",
                "name": "Product & Pricing",
                "icon": "💰",
                "description": "Product prices, discounts, promotions",
                "default_patterns": ["harga berapa", "ada diskon", "promo bulan ini"],
                "default_answer": "Untuk info harga dan promo lengkap, silakan kunjungi website www.company.com.",
            },
            {
                "id": "stock",
                "name": "Stock & Availability",
                "icon": "📦",
                "description": "Product availability, pre-order, restock",
                "default_patterns": ["stok ada", "ready barang", "preorder berapa lama"],
                "default_answer": "Stok selalu update real-time di website. Jika tertera 'Ready', barang tersedia.",
            },
            {
                "id": "custom",
                "name": "Custom Category",
                "icon": "✨",
                "description": "Create your own custom FAQ category",
                "default_patterns": [],
                "default_answer": "",
            },
        ]
    }


@router.post("/templates/import")
async def import_faq_template(
    body: dict,
    db: DBSession,
    user: CurrentUser,
    tenant: CurrentTenant,
):
    """Import FAQ from a template."""
    template_id = body.get("template_id")
    
    # Predefined templates
    templates = {
        "retail": {
            "name": "Retail Store Template",
            "categories": ["business_hours", "payment", "shipping", "returns", "contact", "location", "pricing", "stock"],
        },
        "restaurant": {
            "name": "Restaurant Template",
            "categories": ["business_hours", "payment", "location", "contact", "reservation", "menu", "delivery", "allergens"],
        },
        "clinic": {
            "name": "Clinic Template",
            "categories": ["business_hours", "appointment", "services", "insurance", "contact", "location", "pricing", "emergency"],
        },
        "education": {
            "name": "Education Template",
            "categories": ["business_hours", "admission", "courses", "schedule", "fees", "contact", "location", "requirements"],
        },
    }
    
    if template_id not in templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template. Available: {list(templates.keys())}",
        )
    
    template = templates[template_id]
    imported_count = 0
    
    # Get default FAQ for each category
    categories_response = await get_faq_categories()
    default_faqs = {cat["id"]: cat for cat in categories_response["categories"]}
    
    for category_id in template["categories"]:
        if category_id in default_faqs:
            default = default_faqs[category_id]
            
            # Check if FAQ already exists for this category
            existing = await db.execute(
                select(TenantFAQ).where(
                    TenantFAQ.tenant_id == tenant.id,
                    TenantFAQ.category == category_id
                )
            )
            
            if not existing.scalar_one_or_none():
                faq = TenantFAQ(
                    tenant_id=tenant.id,
                    category=category_id,
                    question_patterns=default["default_patterns"],
                    answer=default["default_answer"],
                    confidence=0.9,
                    is_active=True,
                )
                db.add(faq)
                imported_count += 1
    
    await db.commit()
    
    logger.info("Imported %d FAQ from template %s for tenant %s", imported_count, template_id, tenant.id)
    
    return {
        "message": f"Imported {imported_count} FAQ from {template['name']}",
        "template": template["name"],
        "imported_count": imported_count,
    }

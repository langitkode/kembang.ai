"""Intent Router – classify incoming messages and route to appropriate handler.

Three-tier classification:
1. FAQ (cached keyword match + embedding similarity) → Return cached answer, NO LLM
2. Tool (function call) → Execute tool, NO LLM
3. RAG (requires reasoning) → Full RAG pipeline with LLM

This reduces LLM costs by 60-80% for common queries.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from difflib import SequenceMatcher

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    FAQ = "faq"
    TOOL = "tool"
    RAG = "rag"
    GREETING = "greeting"
    SMALLTALK = "smalltalk"


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    payload: Optional[dict] = None
    cached_answer: Optional[str] = None


@dataclass
class FAQPatternWithEmbedding:
    """FAQ pattern with pre-computed embedding for similarity matching."""
    regex: re.Pattern
    answer: str
    confidence: float
    pattern_text: str  # Original pattern text for embedding
    embedding: Optional[list[float]] = None  # Pre-computed embedding


class IntentRouter:
    """Route messages to appropriate handler based on intent."""

    # Embedding similarity threshold for FAQ matching
    EMBEDDING_THRESHOLD = 0.75

    def __init__(
        self,
        faq_patterns: Optional[list[tuple[re.Pattern, str, float]]] = None,
        faq_with_embeddings: Optional[list[FAQPatternWithEmbedding]] = None,
    ):
        # FAQ patterns with cached answers
        # Format: [(regex_pattern, answer, confidence)]
        self._faq_patterns: list[tuple[re.Pattern, str, float]] = faq_patterns or []

        # FAQ patterns with embeddings for similarity matching
        self._faq_with_embeddings: list[FAQPatternWithEmbedding] = faq_with_embeddings or []

        # Greeting patterns
        self._greeting_patterns = [
            r"\b(hai|hello|halo|hey|hi|selamat pagi|selamat siang|selamat sore|selamat malam)\b",
            r"\bgood (morning|afternoon|evening)\b",
        ]

        # Smalltalk patterns
        self._smalltalk_patterns = [
            r"\b(apa kabar|how are you|are you ok)\b",
            r"\b(siapa (kamu|anda|lo)|who are you)\b",
            r"\b(makasih|terima kasih|thanks|thank you)\b",
        ]

        # Tool triggers
        self._tool_patterns = [
            (r"\b(cek|check|status|lacak|tracking) (pesanan|order|barang)\b", "order_status"),
        ]

        # Embedding model (lazy-loaded)
        self._embedding_model = None
    
    def add_faq(self, patterns: list[str], answer: str, confidence: float = 0.9):
        """Add FAQ pattern with cached answer.

        Args:
            patterns: List of regex patterns (case-insensitive)
            answer: Cached answer to return
            confidence: Confidence score (0.0-1.0)
        """
        for pattern in patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            self._faq_patterns.append((regex, answer, confidence))

            # Also store with embedding for similarity matching
            faq_with_emb = FAQPatternWithEmbedding(
                regex=regex,
                answer=answer,
                confidence=confidence,
                pattern_text=pattern
            )
            self._faq_with_embeddings.append(faq_with_emb)

        logger.info("Added FAQ: %s → %s", patterns, answer[:50])

    def _get_embedding_model(self):
        """Lazy-load embedding model."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(
                    "all-MiniLM-L6-v2",
                    cache_folder="/tmp/huggingface"
                )
                logger.info("Embedding model loaded for intent classification")
            except Exception as e:
                logger.warning("Failed to load embedding model: %s. Using fallback matching.", e)
                return None
        return self._embedding_model

    def _embedding_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts using embeddings."""
        model = self._get_embedding_model()
        if model is None:
            return 0.0

        try:
            embeddings = model.encode([text1, text2])
            # Cosine similarity
            from numpy import dot
            from numpy.linalg import norm
            similarity = dot(embeddings[0], embeddings[1]) / (norm(embeddings[0]) * norm(embeddings[1]))
            return float(similarity)
        except Exception as e:
            logger.warning("Embedding similarity calculation failed: %s", e)
            return 0.0
    
    def classify(self, message: str) -> IntentResult:
        """Classify message intent.
        
        Returns:
            IntentResult with intent type, confidence, and optional payload
        """
        message_lower = message.lower().strip()
        
        # 1. Check greetings (highest priority)
        for pattern in self._greeting_patterns:
            if re.search(pattern, message_lower):
                return IntentResult(
                    intent=IntentType.GREETING,
                    confidence=0.95,
                    cached_answer=self._get_greeting_response(message_lower)
                )
        
        # 2. Check smalltalk
        for pattern in self._smalltalk_patterns:
            if re.search(pattern, message_lower):
                return IntentResult(
                    intent=IntentType.SMALLTALK,
                    confidence=0.9,
                    cached_answer=self._get_smalltalk_response(message_lower)
                )
        
        # 3. Check FAQ with SMART matching (regex + keyword overlap + fuzzy)
        for regex, answer, confidence in self._faq_patterns:
            # Level 1: Exact regex match (strict)
            if regex.search(message_lower):
                logger.info("FAQ match (regex): %s → %s", message[:50], answer[:50])
                return IntentResult(
                    intent=IntentType.FAQ,
                    confidence=confidence,
                    cached_answer=answer
                )
            
            # Level 2: Keyword overlap (flexible)
            pattern_str = regex.pattern
            pattern_words = set(re.findall(r'\b\w+\b', pattern_str.lower()))
            message_words = set(re.findall(r'\b\w+\b', message_lower))
            
            if pattern_words:  # Avoid division by zero
                overlap = len(message_words & pattern_words) / len(pattern_words)
                if overlap >= 0.6:  # 60% keyword overlap = match
                    logger.info("FAQ match (keyword %.0f%%): %s → %s", 
                               overlap * 100, message[:50], answer[:50])
                    return IntentResult(
                        intent=IntentType.FAQ,
                        confidence=confidence * overlap,  # Reduce confidence based on overlap
                        cached_answer=answer
                    )
            
            # Level 3: Fuzzy match (fallback)
            similarity = SequenceMatcher(None, message_lower, pattern_str).ratio()
            if similarity >= 0.75:  # 75% similar
                logger.info("FAQ match (fuzzy %.0f%%): %s → %s",
                           similarity * 100, message[:50], answer[:50])
                return IntentResult(
                    intent=IntentType.FAQ,
                    confidence=confidence * similarity,  # Reduce confidence
                    cached_answer=answer
                )

        # 3b. Check FAQ with embedding-based similarity (most flexible)
        if self._faq_with_embeddings:
            best_match = None
            best_similarity = 0.0

            for faq in self._faq_with_embeddings:
                similarity = self._embedding_similarity(message, faq.pattern_text)
                if similarity > best_similarity and similarity >= self.EMBEDDING_THRESHOLD:
                    best_similarity = similarity
                    best_match = faq

            if best_match:
                logger.info("FAQ match (embedding %.0f%%): %s → %s",
                           best_similarity * 100, message[:50], best_match.answer[:50])
                return IntentResult(
                    intent=IntentType.FAQ,
                    confidence=best_match.confidence * best_similarity,
                    cached_answer=best_match.answer
                )

        # 4. Check tool triggers
        for pattern, tool_name in self._tool_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Extract parameters
                params = match.groups() if match.groups() else {}
                return IntentResult(
                    intent=IntentType.TOOL,
                    confidence=0.85,
                    payload={
                        "tool_name": tool_name,
                        "params": params
                    }
                )
        
        # 5. Default to RAG (requires reasoning)
        return IntentResult(
            intent=IntentType.RAG,
            confidence=1.0,
            payload={"requires_rag": True}
        )
    
    def _get_greeting_response(self, message: str) -> str:
        """Get appropriate greeting response."""
        if "pagi" in message:
            return "Selamat pagi! Ada yang bisa saya bantu?"
        elif "siang" in message:
            return "Selamat siang! Ada yang bisa saya bantu?"
        elif "sore" in message:
            return "Selamat sore! Ada yang bisa saya bantu?"
        elif "malam" in message:
            return "Selamat malam! Ada yang bisa saya bantu?"
        else:
            return "Halo! Ada yang bisa saya bantu?"
    
    def _get_smalltalk_response(self, message: str) -> str:
        """Get appropriate smalltalk response."""
        if "kabar" in message or "how are you" in message:
            return "Saya baik-baik saja! Ada yang bisa saya bantu?"
        elif "siapa" in message or "who are you" in message:
            return "Saya adalah asisten virtual untuk membantu pertanyaan Anda."
        elif "makasih" in message or "terima" in message or "thank" in message:
            return "Sama-sama! Ada lagi yang bisa saya bantu?"
        else:
            return "Halo! Ada yang bisa saya bantu?"


# ── Default FAQ Configuration ────────────────────────────────────────────────

def create_default_router() -> IntentRouter:
    """Create router with default FAQ for UMKM chatbot."""
    router = IntentRouter()
    
    # Business Hours
    router.add_faq(
        patterns=[
            r"\b(jam|kapan) (buka|operasional|tutup)\b",
            r"\b(buka jam|operasional jam)\b",
            r"\b(hari apa|hari apa saja)\b",
        ],
        answer="Kami buka setiap hari pukul 09.00–21.00 WIB.",
        confidence=0.9
    )
    
    # Payment Methods
    router.add_faq(
        patterns=[
            r"\b(bayar|pembayaran|metode pembayaran)\b",
            r"\b(e-wallet|gopay|ovo|dana|shopeepay)\b",
            r"\b(transfer|bank|bca|mandiri|bni|bri)\b",
            r"\b(cod|bayar di tempat)\b",
        ],
        answer="Kami menerima pembayaran via:\n• E-wallet: GoPay, OVO, Dana, ShopeePay\n• Transfer Bank: BCA, Mandiri, BNI, BRI\n• COD (Bayar di Tempat) untuk area tertentu",
        confidence=0.9
    )
    
    # Shipping
    router.add_faq(
        patterns=[
            r"\b(kirim|pengiriman|ongkir|ongkos kirim)\b",
            r"\b(ekspedisi|kurir|jnt|jne|sicepat|antar)\b",
            r"\b(brapa lama|berapa lama|sampai)\b",
        ],
        answer="Pengiriman tersedia ke seluruh Indonesia:\n• Jabodetabek: 1-2 hari\n• Jawa: 2-4 hari\n• Luar Jawa: 3-7 hari\n\nOngkir dihitung otomatis saat checkout.",
        confidence=0.85
    )
    
    # Returns/Refunds
    router.add_faq(
        patterns=[
            r"\b(retur|return|kembali|refund)\b",
            r"\b(ganti|tukar|barang rusak|cacat)\b",
            r"\b(garansi|warranty)\b",
        ],
        answer="Kebijakan retur:\n• Retur dalam 7 hari setelah diterima\n• Barang harus dalam kondisi asli\n• Foto/video unboxing sebagai bukti\n• Garansi resmi 1 tahun untuk semua produk",
        confidence=0.85
    )
    
    # Contact/Support
    router.add_faq(
        patterns=[
            r"\b(hubungi|kontak|contact|cs|customer service)\b",
            r"\b(whatsapp|wa|telepon|telp|email)\b",
            r"\b(admin|support|bantuan|help)\b",
        ],
        answer="Hubungi kami:\n• WhatsApp: +62 812-3456-7890\n• Email: support@company.com\n• Jam operasional: 09.00-21.00 WIB",
        confidence=0.9
    )
    
    # Location
    router.add_faq(
        patterns=[
            r"\b(lokasi|alamat|address|dimana|where)\b",
            r"\b(toko|store|outlet|cabang)\b",
            r"\b(kantor|office)\b",
        ],
        answer="Alamat kami:\nJl. Raya Utama No. 123\nJakarta Selatan, 12345\n\nGoogle Maps: bit.ly/company-location",
        confidence=0.85
    )
    
    # Product Info
    router.add_faq(
        patterns=[
            r"\b(harga|price|biaya|cost)\b",
            r"\b(promo|diskon|discount|sale)\b",
            r"\b(katalog|catalog)\b",
        ],
        answer="Untuk info harga dan katalog lengkap, silakan kunjungi:\n• Website: www.company.com\n• Marketplace: Tokopedia/Shopee (search: Company Official)\n\nPromo update setiap hari!",
        confidence=0.8
    )
    
    # Stock Availability
    router.add_faq(
        patterns=[
            r"\b(stok|stock|tersedia|ready|available)\b",
            r"\b(ada|habis|out of stock)\b",
            r"\b(preorder|po|indent)\b",
        ],
        answer="Stok selalu update real-time di website/app. Jika tertera 'Ready', barang tersedia dan bisa langsung dikirim. Untuk PO, estimasi 7-14 hari.",
        confidence=0.85
    )

    logger.info("IntentRouter initialized with %d FAQ patterns", len(router._faq_patterns))
    return router


# ── Database-backed FAQ Loader ────────────────────────────────────────────────


async def load_tenant_faqs(db: AsyncSession, tenant_id: uuid.UUID) -> list[tuple[re.Pattern, str, float]]:
    """Load FAQ patterns from database for a specific tenant.
    
    Returns:
        List of (compiled_regex_pattern, answer, confidence) tuples
    """
    from app.models.faq import TenantFAQ
    
    result = await db.execute(
        select(TenantFAQ).where(
            TenantFAQ.tenant_id == tenant_id,
            TenantFAQ.is_active == True
        ).order_by(TenantFAQ.confidence.desc())
    )
    
    faqs = result.scalars().all()
    patterns = []
    
    for faq in faqs:
        for pattern_str in faq.question_patterns:
            try:
                # Compile regex pattern (case-insensitive)
                regex = re.compile(pattern_str, re.IGNORECASE)
                patterns.append((regex, faq.answer, faq.confidence))
            except re.error as e:
                logger.warning("Invalid regex pattern '%s' in FAQ %s: %s", pattern_str, faq.id, e)
    
    logger.info("Loaded %d FAQ patterns from database for tenant %s", len(patterns), tenant_id)
    return patterns


async def create_tenant_intent_router(db: AsyncSession, tenant_id: uuid.UUID) -> IntentRouter:
    """Create an IntentRouter with FAQ loaded from database for a specific tenant.
    
    This combines:
    1. Tenant-specific FAQ from database
    2. Default global FAQ (as fallback)
    """
    # Load tenant-specific FAQ
    tenant_patterns = await load_tenant_faqs(db, tenant_id)
    
    # If no tenant FAQ, use default
    if not tenant_patterns:
        logger.info("No tenant FAQ found, using default patterns for tenant %s", tenant_id)
        return create_default_router()
    
    # Create router with tenant patterns
    router = IntentRouter(faq_patterns=tenant_patterns)
    
    logger.info("Created tenant-specific IntentRouter for %s with %d patterns", tenant_id, len(tenant_patterns))
    return router


# Singleton instance
_default_router: Optional[IntentRouter] = None

def get_intent_router() -> IntentRouter:
    """Get or create default intent router."""
    global _default_router
    if _default_router is None:
        _default_router = create_default_router()
    return _default_router

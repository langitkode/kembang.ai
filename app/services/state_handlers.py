"""State handlers - generate responses based on conversation state."""

import logging
from typing import Optional
from app.services.conversation_state_machine import ConversationState, ConversationStage, ConversationSlots
from app.services.slot_extractor import SlotExtractor, get_slot_extractor
from app.services.product_service import ProductService, format_product_list, format_product_detail
from app.services.catalog_service import CatalogService

logger = logging.getLogger(__name__)


class StateHandler:
    """Handle responses for each conversation state."""
    
    def __init__(self, db=None, tenant_id=None):
        self._db = db
        self._tenant_id = tenant_id
        self._product_service = ProductService(db) if db else None
        self._catalog_metadata = None
        self._slot_extractor = get_slot_extractor()  # Initialize with defaults
        self._initialized = False
    
    async def initialize(self):
        """Initialize catalog metadata (call this before first use)."""
        if self._initialized:
            return
        
        if self._db and self._tenant_id:
            try:
                catalog_service = CatalogService(self._db)
                self._catalog_metadata = await catalog_service.get_catalog_metadata(self._tenant_id)
                self._slot_extractor = get_slot_extractor(self._catalog_metadata)
                logger.info("StateHandler initialized with catalog metadata for tenant %s", self._tenant_id)
            except Exception as e:
                logger.warning("Failed to load catalog metadata: %s. Using defaults.", e)
        
        self._initialized = True
    
    def handle_state(
        self,
        state: ConversationState,
        user_message: str,
        context_from_rag: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle response based on current state.
        
        Returns:
            (response_text, updated_state)
        """
        handler_map = {
            ConversationStage.INIT: self._handle_init,
            ConversationStage.GREETING_DONE: self._handle_greeting_done,
            ConversationStage.ASKING_PRODUCT: self._handle_asking_product,
            ConversationStage.ASKING_BUDGET: self._handle_asking_budget,
            ConversationStage.SHOWING_PRODUCTS: self._handle_showing_products,
            ConversationStage.PRODUCT_DETAIL: self._handle_product_detail,
            ConversationStage.CHECKOUT: self._handle_checkout,
            ConversationStage.ASKING_LOCATION: self._handle_asking_location,
            ConversationStage.ASKING_CONTACT: self._handle_asking_contact,
            ConversationStage.HAND_OFF_TO_ADMIN: self._handle_hand_off,
        }
        
        handler = handler_map.get(state.stage, self._handle_rag_fallback)
        return handler(state, user_message, context_from_rag)
    
    def _handle_init(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle INIT state - send greeting."""
        response = (
            "Halo! 👋 Selamat datang! \n\n"
            "Saya asisten virtual siap membantu kamu menemukan produk yang cocok. "
            "Ada yang bisa saya bantu hari ini? 😊"
        )
        state.stage = ConversationStage.GREETING_DONE
        return response, state
    
    def _handle_greeting_done(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle GREETING_DONE - user just greeted, check their query."""
        # Extract slots from first query
        state.slots = self.slot_extractor.extract(user_message, state.slots)
        
        # If user asked about product, move to ASKING_PRODUCT
        if state.slots.product_type:
            state.stage = ConversationStage.ASKING_PRODUCT
            return self._handle_asking_product(state, user_message, context)
        
        # If user asked about location
        if any(word in user_message.lower() for word in ["lokasi", "alamat", "toko", "cabang"]):
            state.stage = ConversationStage.ASKING_LOCATION
            return self._handle_asking_location(state, user_message, context)
        
        # Otherwise, use RAG context
        if context:
            state.stage = ConversationStage.ASKING_PRODUCT
            return f"{context}\n\nAda yang mau ditanyakan lagi? 😊", state
        
        # Fallback
        state.stage = ConversationStage.ASKING_PRODUCT
        return "Boleh tahu kamu lagi cari produk apa? 📦", state
    
    def _handle_asking_product(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle ASKING_PRODUCT - gather product requirements."""
        # Extract slots
        state.slots = self.slot_extractor.extract(user_message, state.slots)
        
        # Check what we have
        if state.slots.product_type and not state.slots.skin_type:
            # Got product type, ask skin type
            state.stage = ConversationStage.ASKING_PRODUCT
            product = state.slots.product_type.title()
            return (
                f"Oke, untuk {product}, kamu punya jenis kulit apa? 🤔\n"
                "- Berminyak\n"
                "- Kering\n"
                "- Normal\n"
                "- Sensitif"
            ), state
        
        if state.slots.product_type and state.slots.skin_type and not state.slots.budget_min:
            # Got product + skin type, ask budget
            state.stage = ConversationStage.ASKING_BUDGET
            return (
                "Got it! Budget berapa untuk produk ini? 💰\n"
                "(contoh: 50k, 100ribuan, di bawah 200k)"
            ), state
        
        if state.slots.product_type and state.slots.skin_type and state.slots.budget_min:
            # Got all info, show products
            state.stage = ConversationStage.SHOWING_PRODUCTS
            return self._handle_showing_products(state, user_message, context)
        
        # Not enough info yet
        if not state.slots.product_type:
            return (
                "Kamu lagi cari produk apa? 📦\n"
                "(skincare, makeup, bodycare, atau haircare?)"
            ), state
        
        return "Ada yang mau ditanyakan lagi tentang produk ini? 😊", state
    
    def _handle_asking_budget(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle ASKING_BUDGET - gather budget info."""
        # Extract budget
        state.slots = self.slot_extractor.extract(user_message, state.slots)
        
        if state.slots.budget_min is not None:
            # Got budget, show products
            state.stage = ConversationStage.SHOWING_PRODUCTS
            return self._handle_showing_products(state, user_message, context)
        
        # Ask again
        return (
            "Budgetnya berapa? 💰\n"
            "(contoh: 50k, 100ribuan, di bawah 200k)"
        ), state
    
    async def _handle_showing_products(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle SHOWING_PRODUCTS - display product recommendations."""
        # Use product service if available
        if self._product_service and self._db:
            # Search products based on slots
            from app.db.session import async_session_factory
            async with async_session_factory() as db:
                product_service = ProductService(db)
                products = await product_service.search_products(
                    tenant_id=db.bind.params.get('tenant_id') if hasattr(db.bind, 'params') else None,  # Will be set by caller
                    slots=state.slots,
                    limit=5,
                )
                
                if products:
                    response = format_product_list(products, "Oke, ini rekomendasiku untuk kamu! 🎉")
                    state.context["shown_products"] = [str(p.id) for p in products]
                else:
                    response = (
                        "Maaf, saya belum punya produk yang cocok di katalog. 😅\n\n"
                        "Tapi tenang, tim kami siap bantu kamu pilih produk yang tepat!\n\n"
                        "Mau saya sambungkan ke customer service? 😊"
                    )
        else:
            # Fallback without product service
            if context:
                response = (
                    f"Oke, ini rekomendasiku untuk kamu! 🎉\n\n{context}\n\n"
                    "Mau lihat detail produk mana? Atau langsung pesan? 😊"
                )
            else:
                response = (
                    f"Berdasarkan kebutuhan kamu:\n"
                    f"- Produk: {state.slots.product_type}\n"
                    f"- Kulit: {state.slots.skin_type}\n"
                    f"- Budget: Rp {state.slots.budget_min:,.0f} - {state.slots.budget_max:,.0f}\n\n"
                    "Sayang saya belum punya katalog lengkap di sini. "
                    "Boleh cek website atau marketplace kami ya! 🛒"
                )
        
        state.stage = ConversationStage.PRODUCT_DETAIL
        return response, state
    
    def _handle_product_detail(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle PRODUCT_DETAIL - show specific product details."""
        # Extract selected product
        state.slots = self.slot_extractor.extract(user_message, state.slots)
        
        if context:
            response = f"Detail produk:\n\n{context}\n\nMau pesan? ✅"
        else:
            response = (
                f"Produk {state.slots.selected_product_name or 'ini'} tersedia! 📦\n"
                "Mau pesan sekarang? 😊"
            )
        
        # Check if user wants to buy
        if any(word in user_message.lower() for word in ["pesan", "beli", "ambil", "order", "checkout"]):
            state.stage = ConversationStage.CHECKOUT
        
        return response, state
    
    def _handle_checkout(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle CHECKOUT - guide through purchase flow."""
        # Check what info we have
        if not state.slots.customer_name:
            state.stage = ConversationStage.ASKING_CONTACT
            return (
                "Siap! Untuk proses pesanan, boleh tahu nama kamu? 😊"
            ), state
        
        if not state.slots.customer_phone:
            return (
                f"Hai {state.slots.customer_name}! Nomor WhatsApp kamu berapa ya? 📱\n"
                "(untuk konfirmasi pesanan)"
            ), state
        
        if not state.slots.shipping_address:
            return (
                "Terakhir, kirim ke mana ya? 📍\n"
                "(tuliskan alamat lengkap)"
            ), state
        
        # All info collected
        state.stage = ConversationStage.COMPLETE
        return (
            "Pesanan kamu sudah kami terima! ✅\n\n"
            "Tim kami akan segera menghubungi kamu via WhatsApp untuk konfirmasi. "
            "Terima kasih sudah berbelanja! 🎉"
        ), state
    
    def _handle_asking_location(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle ASKING_LOCATION - location/store inquiry."""
        if context:
            response = f"Informasi lokasi:\n\n{context}\n\nAda yang bisa dibantu lagi? 😊"
        else:
            response = (
                "Lokasi toko kami:\n"
                "📍 Jl. Raya Utama No. 123, Jakarta Selatan\n\n"
                "Buka setiap hari 09.00-21.00 WIB. ⏰\n\n"
                "Mau tanya hal lain? 😊"
            )
        
        state.stage = ConversationStage.GREETING_DONE
        return response, state
    
    def _handle_asking_contact(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle ASKING_CONTACT - collect contact info."""
        # Extract name/phone from message
        state.slots = self.slot_extractor.extract(user_message, state.slots)
        
        if not state.slots.customer_name:
            # Try to extract name from message
            state.slots.customer_name = user_message.strip()
            return (
                f"Hai {state.slots.customer_name}! Senang berkenalan dengan kamu! 😊\n"
                "Nomor WhatsApp kamu berapa ya? 📱"
            ), state
        
        if not state.slots.customer_phone:
            state.slots.customer_phone = user_message.strip()
            return (
                "Siap! Sekarang boleh tahu alamat pengiriman lengkapnya? 📍"
            ), state
        
        state.stage = ConversationStage.CHECKOUT
        return self._handle_checkout(state, user_message, context)
    
    def _handle_hand_off(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Handle HAND_OFF_TO_ADMIN - escalate to human."""
        response = (
            "Baik, saya akan sambungkan kamu dengan tim customer service kami. 🙏\n\n"
            "Silakan hubungi:\n"
            "📱 WhatsApp: +62 812-3456-7890\n"
            "📧 Email: support@company.com\n\n"
            "Tim kami siap membantu (09.00-21.00 WIB). Terima kasih! 😊"
        )
        # Stay in HAND_OFF state
        return response, state
    
    def _handle_rag_fallback(
        self,
        state: ConversationState,
        user_message: str,
        context: Optional[str] = None,
    ) -> tuple[str, ConversationState]:
        """Fallback to RAG response when no state handler matches."""
        if context:
            return context, state
        return "Maaf, saya kurang mengerti. Bisa tanya lebih spesifik? 🤔", state


# Global instance
_default_handler = None


def get_state_handler() -> StateHandler:
    """Get or create global state handler."""
    global _default_handler
    if _default_handler is None:
        _default_handler = StateHandler()
        logger.info("State handler initialized")
    return _default_handler

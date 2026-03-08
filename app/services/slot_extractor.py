"""Slot extractor - extract entities from user messages for sales flow.

Hybrid approach:
1. Default keywords for cold start
2. Dynamic learning from product catalog
3. Tenant-specific customization
"""

import re
import logging
from typing import Optional
from app.services.conversation_state_machine import ConversationSlots

logger = logging.getLogger(__name__)


class SlotExtractor:
    """Extract entities/slots from user messages."""
    
    # Default product types (fallback if catalog is empty)
    DEFAULT_PRODUCT_TYPES = {
        "skincare": ["skincare", "perawatan wajah", "serum", "toner", "moisturizer", "sunscreen", "face wash"],
        "makeup": ["makeup", "kosmetik", "lipstick", "foundation", "bedak", "mascara"],
        "bodycare": ["bodycare", "perawatan tubuh", "body lotion", "body scrub"],
        "haircare": ["haircare", "perawatan rambut", "sampo", "kondisioner", "hair tonic"],
    }
    
    # Default skin types (fallback)
    DEFAULT_SKIN_TYPES = {
        "berminyak": ["berminyak", "minyak", "oily", "kilap"],
        "kering": ["kering", "dry", "ketombe", "bersisik"],
        "normal": ["normal", "kombinasi", "combination"],
        "sensitif": ["sensitif", "sensitive", "mudah iritasi", "merah"],
        "berjerawat": ["berjerawat", "acne", "jerawat", "breakout"],
    }
    
    # Default skin concerns (fallback)
    DEFAULT_SKIN_CONCERNS = {
        "jerawat": ["jerawat", "acne", "breakout", "komedo"],
        "whitening": ["whitening", "mencerahkan", "putih", "glowing"],
        "anti_aging": ["anti aging", "kerutan", "usia", "kencang"],
        "hydration": ["hidrasi", "lembab", "kering"],
        "pores": ["pori", "pores", "besar"],
    }
    
    # Budget patterns
    BUDGET_PATTERNS = [
        (r"di bawah (\d+)[kK]?", lambda m: (0, float(m.group(1)) * 1000)),
        (r"(<|kurang dari) (\d+)[kK]?", lambda m: (0, float(m.group(2)) * 1000)),
        (r"(\d+)[kK]?\s*-\s*(\d+)[kK]?", lambda m: (float(m.group(1)) * 1000, float(m.group(2)) * 1000)),
        (r"sekitar (\d+)[kK]?", lambda m: (float(m.group(1)) * 1000 * 0.8, float(m.group(1)) * 1000 * 1.2)),
        (r"(\d+)[kK]?", lambda m: (float(m.group(1)) * 1000, float(m.group(1)) * 1000 * 1.5)),
    ]
    
    # Quantity patterns
    QUANTITY_PATTERNS = [
        r"(\d+)\s*(pcs|buah|paket|set)",
        r"ambil\s*(\d+)",
        r"beli\s*(\d+)",
    ]
    
    def __init__(self, catalog_metadata: Optional[dict] = None):
        """Initialize with optional catalog metadata.
        
        Args:
            catalog_metadata: Dynamic metadata from catalog service
        """
        self._catalog_metadata = catalog_metadata or {}
        
        # Merge default with catalog-based keywords
        self._product_types = self._merge_keywords(
            self.DEFAULT_PRODUCT_TYPES,
            self._catalog_metadata.get("categories", [])
        )
        
        self._skin_types = self._merge_keywords(
            self.DEFAULT_SKIN_TYPES,
            self._catalog_metadata.get("skin_types", [])
        )
        
        self._skin_concerns = self._merge_keywords(
            self.DEFAULT_SKIN_CONCERNS,
            self._catalog_metadata.get("concerns", [])
        )
        
        logger.info("Slot extractor initialized with catalog metadata")
    
    def _merge_keywords(self, defaults: dict, dynamic_values: list) -> dict:
        """Merge default keywords with dynamic catalog values."""
        merged = {k: list(v) for k, v in defaults.items()}
        
        # Add dynamic values as new categories if not in defaults
        for value in dynamic_values:
            value_lower = value.lower()
            
            # Check if value matches any existing keyword
            found = False
            for category, keywords in merged.items():
                if any(kw in value_lower for kw in keywords):
                    found = True
                    break
            
            # Add as new category if not found
            if not found:
                merged[value_lower] = [value_lower]
        
        return merged
    
    def extract(self, message: str, current_slots: ConversationSlots) -> ConversationSlots:
        """Extract slots from user message."""
        try:
            message_lower = message.lower()
            slots = ConversationSlots(**current_slots.dict())
            
            # 1. Extract quantity
            if slots.quantity == 1:
                quantity = self._extract_quantity(message_lower)
                if quantity:
                    slots.quantity = quantity
            
            # 2. Extract selected product
            if not slots.selected_product_id:
                product = self._extract_product_selection(message_lower)
                if product and product not in ['pcs', 'buah', 'paket', 'set']:
                    slots.selected_product_name = product
            
            # 3. Extract budget (only if looks like money)
            if slots.budget_min is None and self._looks_like_budget(message_lower):
                budget = self._extract_budget(message_lower)
                if budget:
                    slots.budget_min, slots.budget_max = budget
            
            # 4. Extract product type
            if not slots.product_type:
                slots.product_type = self._extract_product_type(message_lower)
            
            # 5. Extract skin type
            if not slots.skin_type:
                slots.skin_type = self._extract_skin_type(message_lower)
            
            # 6. Extract skin concern
            if not slots.concern:
                slots.concern = self._extract_skin_concern(message_lower)
            
            logger.debug("Extracted slots: %s", slots.to_dict())
            return slots
        except Exception as e:
            logger.warning("Slot extraction error: %s. Returning current slots.", e)
            return current_slots  # Return original slots on error
    
    def _looks_like_budget(self, message: str) -> bool:
        """Check if message looks like it's about budget."""
        budget_keywords = [
            "budget", "harga", "rp", "ribu", "rb", "k", "juta", "jt",
            "mahal", "murah", "diskon", "promo",
            "di bawah", "kurang dari", "sekitar", "sampai",
        ]
        return any(kw in message for kw in budget_keywords)
    
    def _extract_product_type(self, message: str) -> Optional[str]:
        """Extract product type from message."""
        for product_type, keywords in self._product_types.items():
            if any(kw in message for kw in keywords):
                logger.info("Detected product type: %s", product_type)
                return product_type
        return None
    
    def _extract_skin_type(self, message: str) -> Optional[str]:
        """Extract skin type from message."""
        for skin_type, keywords in self._skin_types.items():
            if any(kw in message for kw in keywords):
                logger.info("Detected skin type: %s", skin_type)
                return skin_type
        return None
    
    def _extract_skin_concern(self, message: str) -> Optional[str]:
        """Extract skin concern from message."""
        for concern, keywords in self._skin_concerns.items():
            if any(kw in message for kw in keywords):
                logger.info("Detected skin concern: %s", concern)
                return concern
        return None
    
    def _extract_budget(self, message: str) -> Optional[tuple[float, float]]:
        """Extract budget range from message."""
        for pattern, extractor in self.BUDGET_PATTERNS:
            match = re.search(pattern, message)
            if match:
                try:
                    budget = extractor(match)
                    logger.info("Detected budget: %s - %s", budget[0], budget[1])
                    return budget
                except Exception as e:
                    logger.warning("Failed to extract budget: %s", e)
        return None
    
    def _extract_quantity(self, message: str) -> Optional[int]:
        """Extract quantity from message."""
        for pattern in self.QUANTITY_PATTERNS:
            match = re.search(pattern, message)
            if match:
                try:
                    quantity = int(match.group(1))
                    logger.info("Detected quantity: %d", quantity)
                    return quantity
                except Exception as e:
                    logger.warning("Failed to extract quantity: %s", e)
        return None
    
    def _extract_product_selection(self, message: str) -> Optional[str]:
        """Extract selected product from message."""
        patterns = [
            r"yang\s+([a-z0-9]+)",
            r"produk\s+([a-z0-9]+)",
            r"ambil\s+([a-z0-9]+)",
            r"nomor\s+(\d+)",
            r"no\s+(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                product = match.group(1)
                logger.info("Detected product selection: %s", product)
                return product
        
        return None
    
    def is_slot_filled(self, slots: ConversationSlots, slot_name: str) -> bool:
        """Check if a specific slot is filled."""
        value = getattr(slots, slot_name, None)
        return value is not None and value != []
    
    def get_missing_slots(self, slots: ConversationSlots, required_slots: list[str]) -> list[str]:
        """Get list of missing required slots."""
        missing = []
        for slot_name in required_slots:
            if not self.is_slot_filled(slots, slot_name):
                missing.append(slot_name)
        return missing


# Global instance
_default_extractor = None


def get_slot_extractor(catalog_metadata: Optional[dict] = None) -> SlotExtractor:
    """Get or create global slot extractor."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = SlotExtractor(catalog_metadata)
        logger.info("Slot extractor initialized")
    return _default_extractor

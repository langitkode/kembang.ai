"""Conversation state machine for sales-oriented chatbot.

Manages conversation flow through sales funnel stages:
INIT → GREETING_DONE → ASKING_PRODUCT → SHOWING_PRODUCTS → CHECKOUT → COMPLETE
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ConversationStage(str, Enum):
    """Sales funnel stages."""
    
    INIT = "init"
    """New conversation - send greeting"""
    
    GREETING_DONE = "greeting_done"
    """Greeting sent - waiting for user query"""
    
    ASKING_PRODUCT = "asking_product"
    """Gathering product requirements (type, skin type, etc.)"""
    
    ASKING_BUDGET = "asking_budget"
    """Gathering budget information"""
    
    SHOWING_PRODUCTS = "showing_products"
    """Displaying product recommendations"""
    
    PRODUCT_DETAIL = "product_detail"
    """Showing specific product details"""
    
    CHECKOUT = "checkout"
    """Purchase flow - collecting order info"""
    
    ASKING_LOCATION = "asking_location"
    """Location/store inquiry flow"""
    
    ASKING_CONTACT = "asking_contact"
    """Collecting contact info for follow-up"""
    
    HAND_OFF_TO_ADMIN = "hand_off_to_admin"
    """Escalate to human admin"""
    
    COMPLETE = "complete"
    """Conversation completed successfully"""


class ConversationSlots(BaseModel):
    """Extracted entities/slots from conversation."""
    
    # Product requirements
    product_type: Optional[str] = None  # "skincare", "makeup", etc.
    skin_type: Optional[str] = None  # "oily", "dry", "sensitive"
    concern: Optional[str] = None  # "acne", "whitening", "anti-aging"
    
    # Budget
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    budget_range: Optional[str] = None  # "<50k", "50k-100k", ">100k"
    
    # Selected items
    selected_product_id: Optional[str] = None
    selected_product_name: Optional[str] = None
    quantity: Optional[int] = 1
    
    # Checkout info
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    
    # Location inquiry
    location_query: Optional[str] = None
    
    # Misc
    shown_products: list[str] = []  # Product IDs shown to user
    last_action: Optional[str] = None
    
    def is_empty(self) -> bool:
        """Check if all slots are empty."""
        return all(v is None or v == [] for v in self.dict().values())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.dict(exclude_none=True)


class ConversationState(BaseModel):
    """Full conversation state."""
    
    stage: ConversationStage = ConversationStage.INIT
    slots: ConversationSlots = ConversationSlots()
    context: dict = {}  # Additional context (e.g., shown_products, last_action)
    retry_count: int = 0  # Number of retries for same state
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "stage": self.stage.value,
            "slots": self.slots.to_dict(),
            "context": self.context,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        """Create from dictionary (from database)."""
        if not data:
            return cls()
        
        return cls(
            stage=ConversationStage(data.get("stage", "init")),
            slots=ConversationSlots(**data.get("slots", {})),
            context=data.get("context", {}),
            retry_count=data.get("retry_count", 0),
        )


# ── State Transition Rules ────────────────────────────────────────────────────

STATE_TRANSITIONS = {
    # From INIT
    ConversationStage.INIT: {
        "greeting": ConversationStage.GREETING_DONE,
        "faq": ConversationStage.GREETING_DONE,
        "rag": ConversationStage.ASKING_PRODUCT,
    },
    
    # From GREETING_DONE
    ConversationStage.GREETING_DONE: {
        "faq": ConversationStage.GREETING_DONE,
        "smalltalk": ConversationStage.GREETING_DONE,
        "rag": ConversationStage.ASKING_PRODUCT,
        "tool": ConversationStage.GREETING_DONE,
    },
    
    # From ASKING_PRODUCT
    ConversationStage.ASKING_PRODUCT: {
        "faq": ConversationStage.GREETING_DONE,
        "rag": ConversationStage.ASKING_BUDGET,  # Got product info, ask budget
    },
    
    # From ASKING_BUDGET
    ConversationStage.ASKING_BUDGET: {
        "faq": ConversationStage.GREETING_DONE,
        "rag": ConversationStage.SHOWING_PRODUCTS,  # Got budget, show products
    },
    
    # From SHOWING_PRODUCTS
    ConversationStage.SHOWING_PRODUCTS: {
        "faq": ConversationStage.GREETING_DONE,
        "rag": ConversationStage.PRODUCT_DETAIL,  # User asks about specific product
        "tool": ConversationStage.CHECKOUT,  # User wants to buy
    },
    
    # From PRODUCT_DETAIL
    ConversationStage.PRODUCT_DETAIL: {
        "tool": ConversationStage.CHECKOUT,  # User wants to buy
        "rag": ConversationStage.SHOWING_PRODUCTS,  # Show more products
    },
    
    # From CHECKOUT
    ConversationStage.CHECKOUT: {
        "faq": ConversationStage.ASKING_CONTACT,  # Collect contact info
        "rag": ConversationStage.ASKING_CONTACT,
    },
    
    # From ASKING_CONTACT
    ConversationStage.ASKING_CONTACT: {
        "rag": ConversationStage.COMPLETE,  # Got contact, complete
    },
    
    # From ASKING_LOCATION
    ConversationStage.ASKING_LOCATION: {
        "faq": ConversationStage.GREETING_DONE,
        "rag": ConversationStage.GREETING_DONE,  # Answered location question
    },
    
    # From HAND_OFF_TO_ADMIN
    ConversationStage.HAND_OFF_TO_ADMIN: {
        "any": ConversationStage.HAND_OFF_TO_ADMIN,  # Stay in this state
    },
}

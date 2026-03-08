"""Response formatter - make LLM responses more human and conversational.

Adds personality, emoji, and natural language variations to responses.
"""

import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Personality Configuration ────────────────────────────────────────────────

PERSONALITY_CONFIG = {
    "tone": "friendly",  # friendly, professional, casual, enthusiastic
    "use_emoji": True,
    "max_length": 150,  # Keep responses concise
    "greeting_style": "warm",  # warm, formal, casual
    "name": "Asisten",  # Bot name
}


# ── Response Templates ───────────────────────────────────────────────────────

RESPONSE_TEMPLATES = {
    "greeting": [
        "Halo! 👋 Ada yang bisa saya bantu?",
        "Hai! Senang bertemu kamu! Mau tanya apa hari ini? 😊",
        "Halo! Saya siap membantu kamu. Ada pertanyaan? 💬",
        "Hi! 👋 Jangan ragu untuk tanya ya!",
        "Halo! Selamat datang! Ada yang bisa saya bantu hari ini? 🌟",
    ],
    "greeting_morning": [
        "Selamat pagi! ☀️ Semangat pagi! Ada yang bisa saya bantu?",
        "Pagi! 🌅 Semoga harimu menyenangkan! Mau tanya apa?",
        "Selamat pagi! Saya siap bantu kamu hari ini! 😊",
    ],
    "greeting_afternoon": [
        "Selamat siang! ☀️ Ada yang bisa saya bantu?",
        "Siang! 🌞 Jangan lupa istirahat ya! Ada pertanyaan?",
        "Selamat siang! Saya siap membantu! 😊",
    ],
    "greeting_evening": [
        "Selamat sore! 🌅 Ada yang bisa saya bantu?",
        "Sore! 🌇 Semoga harimu menyenangkan! Mau tanya apa?",
        "Selamat sore! Saya siap bantu kamu! 😊",
    ],
    "greeting_night": [
        "Selamat malam! 🌙 Ada yang bisa saya bantu?",
        "Malam! 🌟 Jangan lupa istirahat ya! Ada pertanyaan?",
        "Selamat malam! Saya siap membantu! 😊",
    ],
    "thanks": [
        "Sama-sama! Senang bisa membantu! 😊",
        "Terima kasih kembali! Ada lagi yang bisa dibantu? 🙏",
        "Dengan senang hati! 💖 Ada pertanyaan lain?",
        "Santai! 👍 Ada lagi yang mau ditanyakan?",
        "Iya sama-sama! Jangan ragu untuk tanya lagi ya! 😊",
    ],
    "sorry": [
        "Maaf ya, saya belum belajar tentang itu. 🤔 Bisa tanya lebih spesifik?",
        "Waduh, saya kurang tahu tentang ini. 😅 Coba tanya hal lain yuk!",
        "Maaf, informasi ini belum saya pelajari. 📚 Ada pertanyaan lain?",
        "Hmm, saya belum bisa jawab ini. 🤷‍♂️ Tapi saya terus belajar!",
    ],
    "confirmation": [
        "Oke! 👍",
        "Siap! ✅",
        "Baik! 🙏",
        "Mengerti! 💡",
        "Oke, mengerti! 👌",
    ],
    "follow_up": [
        "Ada yang mau ditanyakan lagi? 😊",
        "Ada lagi yang bisa saya bantu? 💬",
        "Jangan ragu untuk tanya lagi ya! 🌟",
        "Saya siap bantu kalau ada pertanyaan lain! 😊",
        "Ada pertanyaan lain? Senang bisa bantu! 💖",
    ],
}


# ── Conversational Fillers ───────────────────────────────────────────────────

FILLERS = {
    "start": [
        "Oke, ",
        "Jadi begini, ",
        "Nah, ",
        "Baik, ",
        "Siap, ",
        "",  # Sometimes no filler
    ],
    "transition": [
        "Jadi, ",
        "Intinya, ",
        "Singkatnya, ",
        "",  # Sometimes no filler
    ],
}


# ── Emoji Mapping ────────────────────────────────────────────────────────────

EMOJI_MAP = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "question": "❓",
    "thinking": "🤔",
    "happy": "😊",
    "sad": "😢",
    "excited": "🎉",
    "love": "💖",
    "thumbs_up": "👍",
    "wave": "👋",
    "sun": "☀️",
    "moon": "🌙",
    "star": "🌟",
    "book": "📚",
    "chat": "💬",
    "package": "📦",
    "money": "💰",
    "time": "⏰",
    "location": "📍",
    "phone": "📞",
    "email": "📧",
}


# ── Response Formatter Class ─────────────────────────────────────────────────

class ResponseFormatter:
    """Format LLM responses to be more human and conversational."""

    def __init__(self, config: Optional[dict] = None):
        """Initialize response formatter.
        
        Args:
            config: Optional personality config override
        """
        self.config = {**PERSONALITY_CONFIG, **(config or {})}
    
    def format(
        self,
        response: str,
        intent: str = "rag",
        context: Optional[dict] = None,
    ) -> str:
        """Format a raw LLM response to be more human.
        
        Args:
            response: Raw LLM response
            intent: Intent type (faq, rag, greeting, etc.)
            context: Optional context (time, user preferences, etc.)
        
        Returns:
            Formatted, more human-like response
        """
        # Skip formatting for empty responses
        if not response or not response.strip():
            return response
        
        # Skip if response is already short and has emoji
        if len(response) < 50 and any(c in response for c in "😀😃😄😁😆😅😂🤣😊"):
            return response
        
        # Apply formatting based on intent
        if intent in ["greeting", "smalltalk"]:
            return self._format_casual(response, context)
        elif intent == "faq":
            return self._format_faq(response, context)
        elif intent == "rag":
            return self._format_rag(response, context)
        else:
            return self._format_default(response, context)
    
    def _format_casual(self, response: str, context: Optional[dict] = None) -> str:
        """Format casual/smalltalk responses."""
        # For greetings, use template if response is generic
        if any(word in response.lower() for word in ["halo", "hai", "hello", "selamat"]):
            template = self._get_greeting_template(context)
            return template
        
        # Add emoji for casual responses
        if self.config["use_emoji"]:
            response = self._add_emoji(response, "happy")
        
        return response
    
    def _format_faq(self, response: str, context: Optional[dict] = None) -> str:
        """Format FAQ responses (keep concise and clear)."""
        # Add emoji based on topic
        if self.config["use_emoji"]:
            if any(word in response.lower() for word in ["jam", "buka", "operasional"]):
                response = self._add_emoji(response, "time")
            elif any(word in response.lower() for word in ["bayar", "pembayaran", "harga"]):
                response = self._add_emoji(response, "money")
            elif any(word in response.lower() for word in ["kirim", "ongkir", "pengiriman"]):
                response = self._add_emoji(response, "package")
            elif any(word in response.lower() for word in ["lokasi", "alamat", "tempat"]):
                response = self._add_emoji(response, "location")
        
        # Keep FAQ responses concise
        if len(response) > self.config["max_length"]:
            response = response[:self.config["max_length"]-3] + "..."
        
        return response
    
    def _format_rag(self, response: str, context: Optional[dict] = None) -> str:
        """Format RAG responses (add personality while keeping accuracy)."""
        # Add conversational starter
        if self.config["tone"] == "friendly":
            filler = random.choice(FILLERS["start"])
            if filler and not response.startswith(("Maaf", "Saya", "Kami")):
                response = filler + response[0].lower() + response[1:]
        
        # Add emoji
        if self.config["use_emoji"] and "maaf" not in response.lower():
            response = self._add_emoji(response, "info")
        
        # Add follow-up for longer responses
        if len(response) > 100 and context and context.get("is_first_message", False):
            follow_up = random.choice(RESPONSE_TEMPLATES["follow_up"])
            response = f"{response}\n\n{follow_up}"
        
        return response
    
    def _format_default(self, response: str, context: Optional[dict] = None) -> str:
        """Default formatting."""
        return response
    
    def _get_greeting_template(self, context: Optional[dict] = None) -> str:
        """Get appropriate greeting template based on time/context."""
        if context and "time_of_day" in context:
            time_key = f"greeting_{context['time_of_day']}"
            if time_key in RESPONSE_TEMPLATES:
                return random.choice(RESPONSE_TEMPLATES[time_key])
        
        return random.choice(RESPONSE_TEMPLATES["greeting"])
    
    def _add_emoji(self, text: str, emoji_type: str) -> str:
        """Add emoji to text."""
        emoji = EMOJI_MAP.get(emoji_type, "")
        if emoji:
            # Add emoji at the end
            text = f"{text} {emoji}"
        return text
    
    def get_thanks_response(self) -> str:
        """Get a random thanks response."""
        return random.choice(RESPONSE_TEMPLATES["thanks"])
    
    def get_sorry_response(self, topic: Optional[str] = None) -> str:
        """Get a random sorry/apology response."""
        return random.choice(RESPONSE_TEMPLATES["sorry"])
    
    def get_follow_up(self) -> str:
        """Get a random follow-up question."""
        return random.choice(RESPONSE_TEMPLATES["follow_up"])


# ── Global Instance ──────────────────────────────────────────────────────────

_default_formatter: Optional[ResponseFormatter] = None


def get_response_formatter() -> ResponseFormatter:
    """Get or create global response formatter."""
    global _default_formatter
    if _default_formatter is None:
        _default_formatter = ResponseFormatter()
        logger.info("Response formatter initialized (tone=%s, emoji=%s)", 
                   _default_formatter.config["tone"],
                   _default_formatter.config["use_emoji"])
    return _default_formatter

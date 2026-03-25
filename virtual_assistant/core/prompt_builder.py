"""
Dynamic system prompt generation for the virtual assistant.

Generates business-specific system prompts and greetings via LLM,
with static fallbacks when LLM is unavailable.
"""

from __future__ import annotations

import logging
from typing import Callable

from .business_config import BusinessConfig

logger = logging.getLogger(__name__)

# Mapping of agent capabilities to their required arguments (for intent routing)
CAPABILITY_ARGS: dict[str, dict[str, str]] = {
    "check_availability": {
        "start_date":    "Start date YYYY-MM-DD (required)",
        "end_date":      "End date YYYY-MM-DD (required)",
        "service_name":  "Service name mentioned by the customer (e.g. 'taglio', 'colore')",
        "service_id":    "Service UUID if already resolved",
        "staff_id":      "Optional staff UUID to filter by a specific stylist",
    },
    "book_appointment": {
        "customer_id":   "Customer UUID (required)",
        "service_id":    "Service UUID (required)",
        "service_name":  "Service name if UUID not yet known",
        "staff_id":      "Staff UUID of the chosen stylist (required)",
        "start_time":    "Appointment start datetime YYYY-MM-DD HH:MM (required)",
        "seat_id":       "Optional seat/postazione UUID",
        "notes":         "Optional customer notes",
    },
    "cancel_appointment": {
        "appointment_id": "Appointment UUID to cancel (required)",
        "customer_id":    "Optional customer UUID for verification",
    },
    "list_services": {},
}


def _get_business_type_str(config: BusinessConfig) -> str:
    """Normalize business_type to string for prompts."""
    bt = config.business_type
    if hasattr(bt, "value"):
        return getattr(bt, "value", str(bt))
    return str(bt)


def _get_tone_str(config: BusinessConfig) -> str:
    """Normalize tone to string for prompts."""
    t = config.tone
    if hasattr(t, "value"):
        return getattr(t, "value", str(t))
    return str(t)


def _get_language_info(lang: str) -> dict[str, str]:
    """Return language name and instruction for meta-prompt."""
    lang_map = {
        "it": ("Italian", "Italian (italiano)"),
        "en": ("English", "English"),
        "es": ("Spanish", "Spanish (español)"),
        "fr": ("French", "French (français)"),
        "de": ("German", "German (Deutsch)"),
    }
    name, full = lang_map.get(lang.lower(), (lang, lang))
    return {"name": name, "instruction": f"Write the entire system prompt in {full}."}


def _get_business_type_guidance(business_type: str) -> str:
    """Return business-type-specific guidance for the meta-prompt."""
    guidance = {
        "salon": (
            "Focus on hair services: haircuts, coloring, treatments, styling. "
            "The assistant should naturally discuss services like taglio, colore, piega, trattamenti. "
            "Use salon-appropriate vocabulary."
        ),
        "clinic": (
            "Focus on medical/dental appointments: check-ups, treatments, consultations. "
            "The assistant should discuss appointments, treatments, availability of doctors/specialists. "
            "Use professional, reassuring language appropriate for healthcare."
        ),
        "restaurant": (
            "Focus on reservations: table booking, party size, dietary preferences, time slots. "
            "The assistant should discuss menus, availability, special requests. "
            "Use welcoming, hospitable language."
        ),
        "hotel": (
            "Focus on room bookings: check-in/out dates, room types, special requests. "
            "The assistant should discuss availability, room options, amenities. "
            "Use professional, hospitable language."
        ),
        "retail": (
            "Focus on orders, product availability, delivery. "
            "The assistant should discuss product catalog, stock, ordering. "
            "Use helpful, customer-service language."
        ),
        "fitness": (
            "Focus on class bookings, gym sessions, personal training. "
            "The assistant should discuss class schedules, availability, memberships. "
            "Use energetic, motivating language."
        ),
    }
    return guidance.get(business_type.lower(), "Tailor the tone and vocabulary to the business type.")


def _build_meta_prompt(config: BusinessConfig) -> str:
    """Build the LLM meta-prompt for generating the system prompt."""
    lang_info = _get_language_info(config.language)
    business_type_str = _get_business_type_str(config)
    tone_str = _get_tone_str(config)
    type_guidance = _get_business_type_guidance(business_type_str)

    services_str = ", ".join(config.services) if config.services else "(not specified)"
    capabilities_str = ", ".join(config.agent_capabilities)
    special = f"\n- Special instructions from the business: {config.special_instructions}" if config.special_instructions else ""

    return f"""You are a meta-prompt engineer. Generate a comprehensive system prompt for a virtual assistant (voice AI) that will handle customer conversations for a specific business.

## Business Information
- **Business name:** {config.name}
- **Business type:** {business_type_str}
- **Services offered:** {services_str}
- **Language:** {config.language} – {lang_info["instruction"]}
- **Tone:** {tone_str}
- **Agent capabilities (actions the assistant can trigger):** {capabilities_str}
{special}

## Business-Type Guidance
{type_guidance}

## Requirements for the Generated System Prompt
The system prompt you generate must:

1. **Persona**: Define who the assistant is (role, tone). If a name is provided, use it. Be consistent with the requested tone ({tone_str}).

2. **Business-specific knowledge**: Include the services offered and how to describe them naturally in conversation. Use vocabulary appropriate for a {business_type_str} business.

3. **Conversation flow**:
   - How to greet customers warmly
   - How to ask for missing information (e.g., service, date, time) without feeling interrogative
   - How to confirm bookings before executing them
   - How to handle "I don't know" or vague requests gracefully

4. **Capability handling**: For each capability ({capabilities_str}), the prompt must clearly instruct the assistant:
   - When to trigger each capability
   - What information must be collected from the customer first
   - How to present results (e.g., available slots, booking confirmation) naturally

5. **Voice / real-time guidelines** (critical for phone calls):
   - Every response must be **1-2 sentences maximum** — the assistant speaks over a phone line
   - No bullet points, lists, or markdown — only natural spoken sentences
   - Ask for one piece of missing information at a time, never multiple questions
   - Be polite, patient, and natural-sounding
   - Never make up information; if uncertain, say you'll check

## Output
Return ONLY the system prompt text — no preamble, no explanation, no markdown headers.
The prompt must be **concise** (aim for ~150 words maximum) and ready to use as a system
message. Write it entirely in the specified language ({config.language})."""


def _build_static_prompt_impl(config: BusinessConfig) -> str:
    """Generate a good default system prompt without calling the LLM."""
    lang = config.language
    business_type_str = _get_business_type_str(config)
    tone_str = _get_tone_str(config)
    services_str = ", ".join(config.services) if config.services else "our services"
    caps = ", ".join(config.agent_capabilities)

    # Base content (language-neutral structure; we'll add language note)
    intro = f"You are the virtual assistant for {config.name}, a {business_type_str} business. "
    intro += f"Your tone is {tone_str}. "
    intro += f"You help customers with: {services_str}. "
    intro += f"You can perform these actions: {caps}."

    persona = f"\n\n## Persona\nYou represent {config.name}. Be {tone_str}, clear, and helpful. Keep responses concise for voice."

    knowledge = f"\n\n## Business Knowledge\nServices offered: {services_str}. Use natural language when discussing them."

    flow = """
## Conversation Flow
- Greet customers warmly.
- If information is missing, ask one question at a time.
- Before booking, confirm: service, date, time (and slot if applicable).
- When you have all required info, trigger the appropriate action.
"""

    capabilities_instruction = f"""
## Capability Handling
- **check_availability**: Collect service (or service name), start date, end date. Then check availability and present options.
- **book_appointment**: Collect customer_id, service, and slot_id. Confirm details, then book.
- Always confirm before executing a booking.
"""

    if config.special_instructions:
        flow += f"\nSpecial instructions: {config.special_instructions}\n"

    lang_note = f"\n\n[Respond in {lang.upper()}]"
    return intro + persona + knowledge + flow + capabilities_instruction + lang_note


def _build_greeting_meta_prompt(config: BusinessConfig, system_prompt: str) -> str:
    """Build the LLM prompt for generating the first greeting."""
    lang_info = _get_language_info(config.language)
    return f"""Generate the FIRST greeting message that the virtual assistant will say when a customer starts a conversation.

Context:
- Business: {config.name}
- Business type: {_get_business_type_str(config)}
- Language: {config.language} – write the greeting in {lang_info["name"]}
- Tone: {_get_tone_str(config)}

The assistant's system prompt (for context):
---
{system_prompt[:1500]}...
---

Requirements:
- One or two short sentences, suitable for voice (easy to say and hear).
- Warm, welcoming, and business-appropriate.
- Invite the customer to say how you can help.
- No preamble or explanation. Output ONLY the greeting text."""


def _build_static_greeting(config: BusinessConfig) -> str:
    """Fallback greeting without LLM."""
    lang = config.language
    name = config.name

    greetings = {
        "it": f"Ciao! Benvenuto da {name}. Come posso aiutarti oggi?",
        "en": f"Hello! Welcome to {name}. How can I help you today?",
        "es": f"¡Hola! Bienvenido a {name}. ¿En qué puedo ayudarte hoy?",
        "fr": f"Bonjour! Bienvenue chez {name}. Comment puis-je vous aider aujourd'hui?",
        "de": f"Hallo! Willkommen bei {name}. Wie kann ich Ihnen heute helfen?",
    }
    return greetings.get(lang.lower(), greetings["en"].replace(name, name))


def _build_router_meta_prompt(config: BusinessConfig) -> str:
    """Build the intent-routing prompt with business capabilities and args."""
    lang = config.language
    lang_info = _get_language_info(config.language)
    caps = config.agent_capabilities

    lines = [
        f"You are an intent router for a voice assistant. The business is {config.name} ({_get_business_type_str(config)}).",
        f"Analyze the customer's utterance and extract the intent. The assistant can perform these actions:",
        "",
    ]

    for cap in caps:
        args_spec = CAPABILITY_ARGS.get(cap, {})
        if args_spec:
            lines.append(f"- **{cap}**:")
            for arg_name, desc in args_spec.items():
                lines.append(f"  - {arg_name}: {desc}")
        else:
            lines.append(f"- **{cap}**: (no required arguments)")

    lines.extend([
        "",
        "Extract these fields when present:",
        "- service_name: Service mentioned (e.g. 'taglio', 'colore', 'check-up')",
        "- service_id: Resolved service ID if known",
        "- start_date, end_date: YYYY-MM-DD for date range",
        "- time_preference: e.g. 'mattina', 'pomeriggio', 'morning'",
        "- staff_preference / staff_id: Preferred staff member",
        "- slot_id: Specific slot if mentioned",
        "- customer_id: Customer ID if provided",
        "- notes: Any additional notes",
        "",
        "Respond ONLY with valid JSON:",
        '{{"action": "<action_name>", "confidence": 0.0-1.0, "args": {{...}}}}',
        "",
        f"Language: {lang_info['instruction']} (for understanding user input; output JSON keys in English)",
    ])

    return "\n".join(lines)


def _build_static_router_prompt(config: BusinessConfig) -> str:
    """Generate a complete, fillable router prompt template without LLM."""
    base = _build_router_meta_prompt(config)
    return base + """

---
The customer said: {user_text}
Customer ID (if known): {customer_id}
Today's date: {today}

JSON:"""


class PromptBuilder:
    """
    Builds business-specific system prompts and greetings using an LLM.

    Can fall back to static templates when the LLM is unavailable or fails.
    """

    def __init__(self, predict_fn: Callable[[str, int], str]):
        """
        Initialize the prompt builder.

        Args:
            predict_fn: LLM caller with signature (prompt: str, max_tokens: int) -> str.
        """
        self._predict = predict_fn
        # Keep generated system prompts short — they are prepended to every LLM call,
        # so a shorter prompt means lower latency on every single turn.
        self._default_max_tokens = 600

    def build_system_prompt(self, business_config: BusinessConfig) -> str:
        """
        Generate a tailored system prompt for the business via LLM.

        Falls back to a static prompt if the LLM call fails.

        Args:
            business_config: Business configuration (name, type, services, etc.).

        Returns:
            The generated system prompt string.
        """
        meta_prompt = _build_meta_prompt(business_config)
        try:
            response = self._predict(meta_prompt, self._default_max_tokens)
            response = response.strip()
            if response:
                return response
        except Exception as e:
            logger.warning("LLM failed to generate system prompt, using static fallback: %s", e)
        return _build_static_prompt_impl(business_config)

    def generate_greeting(
        self,
        business_config: BusinessConfig,
        system_prompt: str,
    ) -> str:
        """
        Generate the first greeting message for the conversation.

        Uses the system prompt as context. Falls back to a static greeting
        if the LLM call fails.

        Args:
            business_config: Business configuration.
            system_prompt: The system prompt (for context).

        Returns:
            The greeting message string.
        """
        meta_prompt = _build_greeting_meta_prompt(business_config, system_prompt)
        try:
            response = self._predict(meta_prompt, 256)
            response = response.strip()
            if response:
                return response
        except Exception as e:
            logger.warning("LLM failed to generate greeting, using static fallback: %s", e)
        return _build_static_greeting(business_config)

    def _build_static_prompt(self, business_config: BusinessConfig) -> str:
        """
        Generate a default system prompt without calling the LLM.

        Use this as a fallback when the LLM is unavailable.

        Args:
            business_config: Business configuration.

        Returns:
            A static but reasonable system prompt.
        """
        return _build_static_prompt_impl(business_config)

    def build_router_prompt(self, business_config: BusinessConfig) -> str:
        """
        Generate the intent-routing prompt that lists agent capabilities
        with their required arguments.

        This prompt is designed to be used with placeholder variables:
        - {user_text}: The customer's utterance
        - {customer_id}: Known customer ID or "unknown"
        - {today}: Today's date in YYYY-MM-DD

        Args:
            business_config: Business configuration.

        Returns:
            The complete router prompt template string.
        """
        return _build_static_router_prompt(business_config)

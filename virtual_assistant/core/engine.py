"""
Main orchestrator for the virtual assistant.

Replaces realtime_assistant.py with a business-configurable flow.
Uses Session (with business_config + system_prompt) for all LLM calls.
"""

from __future__ import annotations

import json
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from .session import ConversationPhase, Session
from .prompt_builder import PromptBuilder
from ..agents.registry import AgentRegistry
from ..agents.tools.availability import AvailabilityTool
from ..voice.stt import transcribe_audio


@dataclass
class TurnResult:
    """Result of processing a conversation turn."""

    user_text: str
    response_text: str
    filler_text: str | None
    action: str | None
    agent_result: Any
    audio_output_path: str | None
    processing_time_ms: float


# Minimal filler phrases by language
_FILLERS: dict[str, list[str]] = {
    "it": [
        "Un attimo, controllo subito...",
        "Fammi verificare...",
        "Vediamo un po'...",
        "Mi dia un momento...",
    ],
    "en": [
        "One moment, let me check...",
        "Let me look into that...",
        "Just a second...",
        "Give me a moment...",
    ],
    "es": [
        "Un momento, voy a verificar...",
        "Déjame comprobar...",
        "Un segundo...",
    ],
    "fr": [
        "Un instant, je vérifie...",
        "Laissez-moi vérifier...",
        "Un moment...",
    ],
    "de": [
        "Einen Moment bitte...",
        "Ich überprüfe das...",
        "Kurz warten...",
    ],
}

# Clarification prompts by language and missing field
_CLARIFICATION: dict[str, dict[str, str]] = {
    "it": {
        "service_id": "Quale servizio vorrebbe prenotare?",
        "slot_id": "Quale orario preferisce?",
        "start_date": "Per quale giorno sarebbe?",
        "end_date": "E fino a quando devo controllare la disponibilità?",
        "customer_id": "Potrei avere il suo nome o codice cliente?",
        "default": "Potrebbe darmi qualche dettaglio in più?",
    },
    "en": {
        "service_id": "Which service would you like to book?",
        "slot_id": "Which time slot do you prefer?",
        "start_date": "Which day are you looking for?",
        "end_date": "Until when should I check availability?",
        "customer_id": "Could I get your name or customer ID?",
        "default": "Could you give me a few more details?",
    },
    "es": {
        "service_id": "¿Qué servicio desea reservar?",
        "slot_id": "¿Qué horario prefiere?",
        "start_date": "¿Para qué día?",
        "end_date": "¿Hasta cuándo debo verificar disponibilidad?",
        "customer_id": "¿Me puede dar su nombre o código de cliente?",
        "default": "¿Podría darme más detalles?",
    },
    "fr": {
        "service_id": "Quel service souhaitez-vous réserver?",
        "slot_id": "Quel créneau préférez-vous?",
        "start_date": "Pour quel jour?",
        "end_date": "Jusqu'à quand dois-je vérifier les disponibilités?",
        "customer_id": "Pouvez-vous me donner votre nom ou identifiant client?",
        "default": "Pourriez-vous me donner plus de détails?",
    },
    "de": {
        "service_id": "Welchen Service möchten Sie buchen?",
        "slot_id": "Welche Uhrzeit bevorzugen Sie?",
        "start_date": "Für welchen Tag?",
        "end_date": "Bis wann soll ich die Verfügbarkeit prüfen?",
        "customer_id": "Könnten Sie mir Ihren Namen oder Ihre Kunden-ID nennen?",
        "default": "Könnten Sie mir noch ein paar Details geben?",
    },
}

# Required and valid params per action (aligned with the new hair salon schema)
_ACTION_REQUIRED: dict[str, list[str]] = {
    "check_availability": ["start_date", "end_date"],           # service_name/id optional filter
    "book_appointment":   ["customer_id", "service_id", "staff_id", "start_time"],
}
_ACTION_PARAMS: dict[str, list[str]] = {
    "check_availability": ["service_id", "service_name", "start_date", "end_date", "staff_id"],
    "book_appointment":   ["customer_id", "service_id", "service_name", "staff_id",
                           "start_time", "seat_id", "notes"],
}


def _default_agent_registry() -> AgentRegistry:
    """Create default registry with availability and booking tools."""
    from ..agents.tools.booking import BookingTool

    reg = AgentRegistry()
    reg.register("check_availability", AvailabilityTool())
    reg.register("book_appointment", BookingTool())
    return reg


def _parse_intent_json(text: str) -> dict[str, Any]:
    """Parse JSON from LLM response."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON found in response: {text[:100]}")
    return json.loads(text[start : end + 1])


class Engine:
    """
    Main orchestrator for the virtual assistant.

    Accepts Session with business_config + system_prompt.
    Uses AgentRegistry for dynamic tool dispatch.
    """

    def __init__(
        self,
        predict_fn: Callable[[str, int], str],
        router_predict_fn: Callable[[str, int], str] | None = None,
        agent_registry: AgentRegistry | None = None,
        tts_manager: Any = None,
    ):
        """
        Initialize the engine.

        Args:
            predict_fn:        LLM caller for responses (prompt, max_tokens) -> str.
            router_predict_fn: LLM caller for JSON intent routing. Defaults to predict_fn.
                               Pass a temperature=0 variant for faster, deterministic routing.
            agent_registry:    Registry for tool dispatch. Defaults to availability + booking.
            tts_manager:       Optional TTS manager for audio output.
        """
        self.predict_fn = predict_fn
        self.router_predict_fn = router_predict_fn or predict_fn
        self.prompt_builder = PromptBuilder(predict_fn)
        self.agent_registry = agent_registry or _default_agent_registry()
        self.tts_manager = tts_manager
        self._availability_tool: AvailabilityTool | None = None

    def _route_intent(self, session: Session, user_text: str, customer_id: str | None) -> dict[str, Any]:
        """Route user text to action with extracted arguments.

        Uses router_predict_fn (temperature=0) with a tight token budget.
        Does NOT include the session system_prompt — routing only needs the
        router template, keeping input tokens minimal for lower latency.
        """
        router_template = self.prompt_builder.build_router_prompt(session.business_config)
        prompt = router_template.format(
            user_text=user_text,
            customer_id=customer_id or "unknown",
            today=date.today().isoformat(),
        )

        # 100 tokens is enough for the JSON output — keeps routing fast
        response = self.router_predict_fn(prompt, 100)
        try:
            result = _parse_intent_json(response)
        except ValueError:
            result = {"action": None, "confidence": 0.0, "args": {}}

        args = result.get("args", {})
        if args.get("service_name") and not args.get("service_id"):
            if self._availability_tool is None:
                self._availability_tool = AvailabilityTool()
            sid = self._availability_tool.resolve_service_id(args["service_name"])
            if sid:
                args["service_id"] = sid
        if customer_id and not args.get("customer_id"):
            args["customer_id"] = customer_id

        result["args"] = args
        return result

    def _get_missing_fields(self, action: str, args: dict[str, Any]) -> list[str]:
        """Get required fields that are missing."""
        required = _ACTION_REQUIRED.get(action, [])
        return [f for f in required if not args.get(f)]

    def _filter_agent_args(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Filter args to valid parameters for the action."""
        allowed = _ACTION_PARAMS.get(action, [])
        return {k: v for k, v in args.items() if k in allowed and v is not None}

    def _generate_filler(self, session: Session) -> str:
        """Generate filler text for wait states."""
        lang = session.business_config.language
        fillers = _FILLERS.get(lang, _FILLERS["en"])
        return random.choice(fillers)

    def _compose_clarification(self, session: Session, missing: list[str], lang: str) -> str:
        """Compose clarification request for missing fields."""
        prompts = _CLARIFICATION.get(lang, _CLARIFICATION["en"])
        for field in missing:
            if field in prompts:
                return prompts[field]
        return prompts.get("default", "Could you give me a few more details?")

    def _compose_agent_response(
        self,
        session: Session,
        action: str,
        agent_result: Any,
    ) -> str:
        """Compose a brief voice response using the session system prompt as context.

        Keeps responses to 1-2 sentences — optimised for real-time phone calls.
        max_tokens=120 is sufficient for a concise spoken reply.
        """
        lang = session.business_config.language
        history = session.format_history_for_prompt()
        user_utterance = session.last_user_utterance

        brevity = "Reply in 1-2 short sentences only. Voice channel — no lists, no markdown."

        if action == "book_appointment":
            if agent_result and agent_result.get("rows_affected", 0) > 0:
                prompt = (
                    f"Booking confirmed. Details: {agent_result}\n"
                    f"History:\n{history}\n\n"
                    f"Confirm the booking naturally in language={lang}, repeating date/time/service. {brevity}"
                )
            else:
                prompt = (
                    f"No availability found. Customer asked: {user_utterance}\n"
                    f"History:\n{history}\n\n"
                    f"Apologise briefly and suggest they try different dates. Language={lang}. {brevity}"
                )
        elif action == "check_availability":
            if agent_result and len(agent_result) > 0:
                # Limit slots shown to avoid huge input tokens
                slots_preview = agent_result[:3]
                prompt = (
                    f"Customer asked: {user_utterance}\n"
                    f"Available slots (first 3): {slots_preview}\n"
                    f"History:\n{history}\n\n"
                    f"Present the options conversationally in language={lang}. {brevity}"
                )
            else:
                prompt = (
                    f"No slots available. Customer asked: {user_utterance}\n"
                    f"History:\n{history}\n\n"
                    f"Apologise and suggest alternatives in language={lang}. {brevity}"
                )
        else:
            prompt = (
                f"Customer: {user_utterance}\nResult: {agent_result}\n"
                f"History:\n{history}\n\n"
                f"Reply naturally in language={lang}. {brevity}"
            )

        full_prompt = f"{session.system_prompt}\n\n{prompt}"
        response = self.predict_fn(full_prompt, 120)
        for prefix in ("Response:", "Risposta:", "Assistant:", "Assistente:"):
            if response.strip().startswith(prefix):
                response = response.strip()[len(prefix):].strip()
        return response.strip()

    def _get_error_message(self, session: Session) -> str:
        """Get generic error message by language."""
        if session.business_config.language == "it":
            return "Mi scusi, non ho capito. Può ripetere per favore?"
        return "Sorry, I didn't understand. Could you repeat?"

    def process_turn(
        self,
        session: Session,
        text_input: str | None = None,
        audio_path: str | None = None,
        customer_id: str | None = None,
    ) -> TurnResult:
        """
        Process a conversation turn.

        Args:
            session: Session with business_config and system_prompt set.
            text_input: User text (alternative to audio).
            audio_path: Path to audio file for transcription.
            customer_id: Optional customer ID.

        Returns:
            TurnResult with all outputs.
        """
        start_time = time.time()

        # 1. Transcribe audio if provided
        if audio_path:
            user_text = transcribe_audio(audio_path, session.business_config.language)
        elif text_input:
            user_text = text_input
        else:
            raise ValueError("Either text_input or audio_path must be provided")

        # 2. Record user turn
        session.add_user_turn(user_text)
        session.phase = ConversationPhase.PROCESSING

        # 3. Route intent
        routed = self._route_intent(session, user_text, customer_id)
        action = routed.get("action")
        args = routed.get("args", {})

        # 4. Check missing required fields
        missing = self._get_missing_fields(action, args) if action else []

        if missing:
            clarification = self._compose_clarification(
                session, missing, session.business_config.language
            )
            session.add_assistant_turn(clarification)

            audio_output = None
            if self.tts_manager:
                result = self.tts_manager.speak(clarification)
                audio_output = result.audio_path if result.success else None

            return TurnResult(
                user_text=user_text,
                response_text=clarification,
                filler_text=None,
                action=action,
                agent_result=None,
                audio_output_path=audio_output,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # 5. If action has agent: generate filler, dispatch agent
        filler_text = None
        agent_result = None
        has_agent = action and self.agent_registry.get(action) is not None

        if has_agent:
            filler_text = self._generate_filler(session)
            if self.tts_manager:
                threading.Thread(
                    target=self.tts_manager.speak_filler,
                    args=(filler_text,),
                    daemon=True,
                ).start()

            session.phase = ConversationPhase.WAITING_FOR_AGENT
            valid_args = self._filter_agent_args(action, args)

            try:
                agent_result = self.agent_registry.execute(action, valid_args)
            except Exception as e:
                agent_result = {"error": str(e)}

        # 6. Compose final response
        session.phase = ConversationPhase.RESPONDING

        if has_agent and agent_result is not None:
            response_text = self._compose_agent_response(session, action, agent_result)
        else:
            response_text = self._get_error_message(session)

        # 7. Record assistant turn
        session.add_assistant_turn(response_text)

        # 8. Generate TTS if available
        audio_output = None
        if self.tts_manager:
            tts_result = self.tts_manager.speak(response_text)
            audio_output = tts_result.audio_path if tts_result.success else None

        session.phase = ConversationPhase.WAITING_FOR_USER

        return TurnResult(
            user_text=user_text,
            response_text=response_text,
            filler_text=filler_text,
            action=action,
            agent_result=agent_result,
            audio_output_path=audio_output,
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    def end_session(self, session: Session) -> str:
        """
        End the session and return farewell.

        Args:
            session: Current session.

        Returns:
            Farewell message.
        """
        lang = session.business_config.language
        farewell = "Grazie per aver chiamato. Buona giornata!" if lang == "it" else "Thank you for calling. Have a great day!"
        session.add_assistant_turn(farewell)
        session.phase = ConversationPhase.ENDED

        if self.tts_manager:
            self.tts_manager.speak(farewell, output_filename="farewell.wav")

        return farewell


# -----------------------------------------------------------------------------
# ConversationEngine: API-layer interface (async, session-id based)
# -----------------------------------------------------------------------------


class ConversationEngine(ABC):
    """
    Async API interface for session-based conversation.
    Used by the FastAPI routes (session ID based).
    """

    @abstractmethod
    async def create_session(
        self,
        business_config: dict[str, Any],
        customer_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create session, generate system prompt, return session_id + greeting."""
        ...

    @abstractmethod
    async def process_turn(
        self,
        session_id: str,
        text: str | None,
        audio_base64: str | None,
        customer_id: str | None,
    ) -> dict[str, Any] | None:
        """Process turn for session. Returns result dict or None if session not found."""
        ...

    @abstractmethod
    async def get_session_summary(self, session_id: str) -> dict[str, Any] | None:
        """Get session summary or None."""
        ...

    @abstractmethod
    async def end_session(self, session_id: str) -> dict[str, Any] | None:
        """End session, return farewell + summary or None."""
        ...


# Global engine for DI
_engine: ConversationEngine | None = None


def init_engine(engine: ConversationEngine) -> None:
    """Set the global conversation engine (used by FastAPI DI)."""
    global _engine
    _engine = engine


def get_engine() -> ConversationEngine:
    """Get the global engine for FastAPI Depends()."""
    if _engine is None:
        raise RuntimeError("Engine not initialized. Call init_engine() at startup.")
    return _engine

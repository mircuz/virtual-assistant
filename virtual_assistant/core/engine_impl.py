"""
Concrete ConversationEngine implementation backed by Databricks LLM + Lakebase.

Flow:
  1. create_session(business_config) → PromptBuilder generates system prompt → Session created
  2. process_turn(session_id, text/audio) → Engine processes turn using system prompt
  3. end_session(session_id) → Engine generates farewell, session removed
"""

from __future__ import annotations

import base64
import os
import tempfile
from typing import Any, Callable

from .business_config import BusinessConfig
from .engine import ConversationEngine, Engine
from .prompt_builder import PromptBuilder
from .session import Session
from ..agents.registry import AgentRegistry
from ..agents.tools.availability import AvailabilityTool
from ..agents.tools.booking import BookingTool


def _build_default_registry() -> AgentRegistry:
    """Build the default agent registry with availability and booking tools."""
    registry = AgentRegistry()
    registry.register("check_availability", AvailabilityTool())
    registry.register("book_appointment", BookingTool())
    return registry


class DatabricksConversationEngine(ConversationEngine):
    """
    Production ConversationEngine backed by Databricks Model Serving and Lakebase.

    Manages in-memory sessions. Each session gets a dynamically generated
    system prompt tailored to the configured business.

    Uses two separate predict functions for minimum latency on phone calls:
      - router_predict_fn: temperature=0, for deterministic JSON intent extraction
      - response_predict_fn: temperature=0.3, for natural conversational replies
    """

    def __init__(
        self,
        predict_fn: Callable[[str, int], str],
        router_predict_fn: Callable[[str, int], str] | None = None,
        agent_registry: AgentRegistry | None = None,
        tts_manager: Any = None,
    ) -> None:
        """
        Initialize the engine.

        Args:
            predict_fn:        LLM caller for responses (prompt, max_tokens) -> str.
            router_predict_fn: LLM caller for intent routing. Defaults to predict_fn
                               with temperature=0 if not provided separately.
            agent_registry:    Tool registry. Defaults to availability + booking.
            tts_manager:       Optional TTS manager for audio output.
        """
        self._predict_fn = predict_fn
        self._router_predict_fn = router_predict_fn or predict_fn
        self._prompt_builder = PromptBuilder(predict_fn)
        self._engine = Engine(
            predict_fn=predict_fn,
            router_predict_fn=self._router_predict_fn,
            agent_registry=agent_registry or _build_default_registry(),
            tts_manager=tts_manager,
        )
        self._sessions: dict[str, Session] = {}

    async def create_session(
        self,
        business_config: dict[str, Any],
        customer_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a new session for the given business.

        Steps:
        1. Build BusinessConfig from the dict.
        2. Call PromptBuilder to generate a tailored system prompt.
        3. Generate an opening greeting.
        4. Store session and return its details.
        """
        config = BusinessConfig(**business_config)

        system_prompt = self._prompt_builder.build_system_prompt(config)
        greeting = self._prompt_builder.generate_greeting(config, system_prompt)

        session = Session(
            business_config=config,
            system_prompt=system_prompt,
            customer_context=customer_context or {},
        )
        session.add_assistant_turn(greeting)
        self._sessions[session.session_id] = session

        return {
            "session_id": session.session_id,
            "generated_system_prompt": system_prompt,
            "greeting": greeting,
            "business_name": config.name,
            "language": config.language,
        }

    async def process_turn(
        self,
        session_id: str,
        text: str | None,
        audio_base64: str | None,
        customer_id: str | None,
    ) -> dict[str, Any] | None:
        """
        Process a conversation turn for the given session.

        Accepts either plain text or base64-encoded audio. Decodes audio
        to a temp WAV file, processes through the Engine, then encodes
        any audio output back to base64.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        audio_path: str | None = None
        tmp_file: str | None = None

        if audio_base64:
            audio_bytes = base64.b64decode(audio_base64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_file = f.name
            audio_path = tmp_file

        try:
            result = self._engine.process_turn(
                session=session,
                text_input=text,
                audio_path=audio_path,
                customer_id=customer_id,
            )
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)

        audio_out_b64: str | None = None
        if result.audio_output_path and os.path.exists(result.audio_output_path):
            with open(result.audio_output_path, "rb") as f:
                audio_out_b64 = base64.b64encode(f.read()).decode()

        return {
            "session_id": session_id,
            "user_text": result.user_text,
            "response_text": result.response_text,
            "filler_text": result.filler_text,
            "action": result.action,
            "audio_base64": audio_out_b64,
            "processing_time_ms": result.processing_time_ms,
            "phase": session.phase.value,
        }

    async def get_session_summary(self, session_id: str) -> dict[str, Any] | None:
        """Return a summary of the session, or None if not found."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        return {
            "session_id": session.session_id,
            "business_name": session.business_config.name,
            "phase": session.phase.value,
            "duration_seconds": session.duration,
            "turn_count": len(session.history),
            "language": session.business_config.language,
        }

    async def end_session(self, session_id: str) -> dict[str, Any] | None:
        """End the session, generate farewell, and remove it from memory."""
        session = self._sessions.pop(session_id, None)
        if session is None:
            return None

        farewell = self._engine.end_session(session)

        return {
            "session_id": session_id,
            "farewell": farewell,
            "summary": {
                "session_id": session_id,
                "business_name": session.business_config.name,
                "phase": session.phase.value,
                "duration_seconds": session.duration,
                "turn_count": len(session.history),
                "language": session.business_config.language,
            },
        }

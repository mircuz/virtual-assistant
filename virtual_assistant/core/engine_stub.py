"""
Stub ConversationEngine for development and testing.

Replace with a real implementation (e.g. virtual_assistant.core.engine_impl)
that wires LLM, TTS, STT from environment variables.
"""

from __future__ import annotations

from typing import Any

from virtual_assistant.core.engine import ConversationEngine


class StubConversationEngine(ConversationEngine):
    """Placeholder engine. Raises NotImplementedError until a real implementation is wired."""

    async def create_session(
        self,
        business_config: dict[str, Any],
        customer_context: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError(
            "Implement ConversationEngine.create_session. "
            "Wire a concrete engine (e.g. from virtual_assistant.core) in app.py startup."
        )

    async def process_turn(
        self,
        session_id: str,
        text: str | None,
        audio_base64: str | None,
        customer_id: str | None,
    ) -> dict[str, Any] | None:
        raise NotImplementedError(
            "Implement ConversationEngine.process_turn. "
            "Wire a concrete engine in app.py startup."
        )

    async def get_session_summary(self, session_id: str) -> dict[str, Any] | None:
        raise NotImplementedError(
            "Implement ConversationEngine.get_session_summary. "
            "Wire a concrete engine in app.py startup."
        )

    async def end_session(self, session_id: str) -> dict[str, Any] | None:
        raise NotImplementedError(
            "Implement ConversationEngine.end_session. "
            "Wire a concrete engine in app.py startup."
        )

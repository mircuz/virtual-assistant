"""Conversation session state management."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Session:
    shop_id: UUID
    shop_config: dict
    session_id: UUID = field(default_factory=uuid4)
    system_prompt: str = ""
    customer: dict | None = None
    caller_phone: str | None = None
    history: list[dict] = field(default_factory=list)
    max_history: int = 20
    # Populated after session start with shop's service/staff lists
    _services: list[str] = field(default_factory=list)
    _staff: list[str] = field(default_factory=list)
    _services_list: list[dict] = field(default_factory=list)
    _staff_list: list[dict] = field(default_factory=list)

    def add_user_turn(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})
        self._trim_history()

    def add_assistant_turn(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})
        self._trim_history()

    def _trim_history(self) -> None:
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def format_for_llm(self) -> list[dict]:
        """Return history formatted for LLM conversation."""
        return [{"role": "system", "content": self.system_prompt}] + self.history


class SessionManager:
    """In-memory session registry."""

    def __init__(self):
        self._sessions: dict[UUID, Session] = {}

    def create_session(
        self, shop_id: UUID, shop_config: dict,
        system_prompt: str = "", caller_phone: str | None = None,
    ) -> UUID:
        session = Session(
            shop_id=shop_id, shop_config=shop_config,
            system_prompt=system_prompt, caller_phone=caller_phone,
        )
        self._sessions[session.session_id] = session
        return session.session_id

    def get_session(self, session_id: UUID) -> Session | None:
        return self._sessions.get(session_id)

    def end_session(self, session_id: UUID) -> None:
        self._sessions.pop(session_id, None)

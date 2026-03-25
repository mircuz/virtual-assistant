"""
Agent registry for mapping action names to agent instances.
"""

from __future__ import annotations

from typing import Any

from .base import BaseAgent


class AgentRegistry:
    """
    Maps string action names to BaseAgent instances.

    Use register() to add agents, get() to retrieve, list_actions() to enumerate.
    """

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, name: str, agent: BaseAgent) -> None:
        """
        Register an agent for an action name.

        Args:
            name: Action name (e.g. "check_availability", "book_appointment")
            agent: BaseAgent instance to invoke
        """
        self._agents[name] = agent

    def get(self, name: str) -> BaseAgent | None:
        """
        Get an agent by action name.

        Args:
            name: Action name

        Returns:
            BaseAgent instance or None if not registered
        """
        return self._agents.get(name)

    def list_actions(self) -> list[str]:
        """Return all registered action names."""
        return list(self._agents.keys())

    def execute(self, name: str, args: dict[str, Any]) -> Any:
        """
        Execute an agent action by name.

        Args:
            name: Action name
            args: Arguments to pass to the agent

        Returns:
            Result from agent.execute()

        Raises:
            KeyError: If action is not registered
        """
        agent = self.get(name)
        if agent is None:
            raise KeyError(f"Unknown action: {name}")
        return agent.execute(args)

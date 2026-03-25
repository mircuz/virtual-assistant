"""
Abstract base for virtual assistant agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Abstract base class for all virtual assistant agents.

    Agents are registered in the AgentRegistry and invoked by action name.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the agent."""
        ...

    @abstractmethod
    def execute(self, args: dict[str, Any]) -> Any:
        """
        Execute the agent's action.

        Args:
            args: Action arguments (e.g. service_id, start_date, etc.)

        Returns:
            Result of the action (structure depends on the agent).
        """
        ...

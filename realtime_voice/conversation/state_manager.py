"""
Conversation State Manager

Central orchestrator that tracks conversation history, pending agent tasks,
user intent state, and turn-taking logic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class ConversationPhase(Enum):
    """Current phase of the conversation."""
    GREETING = "greeting"
    LISTENING = "listening"
    PROCESSING = "processing"
    WAITING_FOR_AGENT = "waiting_for_agent"
    RESPONDING = "responding"
    WAITING_FOR_USER = "waiting_for_user"
    FAREWELL = "farewell"
    ENDED = "ended"


class TaskStatus(Enum):
    """Status of a background agent task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """Represents a background agent task."""
    task_id: str
    agent_name: str
    action: str
    args: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def mark_completed(self, result: Any) -> None:
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = time.time()

    @property
    def elapsed_time(self) -> float:
        """Time elapsed since task creation."""
        end_time = self.completed_at or time.time()
        return end_time - self.created_at


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """
    Complete state of an ongoing conversation.
    
    Tracks history, pending tasks, current intent, and customer context.
    """
    conversation_id: str = field(default_factory=lambda: str(uuid4()))
    language: str = "it"
    phase: ConversationPhase = ConversationPhase.GREETING
    
    # Conversation history
    history: list[ConversationTurn] = field(default_factory=list)
    
    # Current turn state
    last_user_utterance: str = ""
    last_assistant_response: str = ""
    current_intent: dict[str, Any] | None = None
    
    # Pending agent tasks
    pending_tasks: dict[str, AgentTask] = field(default_factory=dict)
    
    # What information we're waiting for from user
    waiting_for: list[str] = field(default_factory=list)
    
    # Customer context (persists across turns)
    customer_context: dict[str, Any] = field(default_factory=dict)
    
    # Timing
    started_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def add_user_turn(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a user turn to history."""
        self.history.append(ConversationTurn(
            role="user",
            content=content,
            metadata=metadata or {}
        ))
        self.last_user_utterance = content
        self.last_activity = time.time()

    def add_assistant_turn(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add an assistant turn to history."""
        self.history.append(ConversationTurn(
            role="assistant",
            content=content,
            metadata=metadata or {}
        ))
        self.last_assistant_response = content
        self.last_activity = time.time()

    def create_task(self, agent_name: str, action: str, args: dict[str, Any]) -> AgentTask:
        """Create and register a new agent task."""
        task = AgentTask(
            task_id=str(uuid4()),
            agent_name=agent_name,
            action=action,
            args=args
        )
        self.pending_tasks[task.task_id] = task
        return task

    def get_pending_tasks(self) -> list[AgentTask]:
        """Get all tasks that are still pending or running."""
        return [
            task for task in self.pending_tasks.values()
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        ]

    def get_completed_tasks(self) -> list[AgentTask]:
        """Get all completed tasks."""
        return [
            task for task in self.pending_tasks.values()
            if task.status == TaskStatus.COMPLETED
        ]

    def has_pending_tasks(self) -> bool:
        """Check if there are any pending or running tasks."""
        return len(self.get_pending_tasks()) > 0

    def get_recent_history(self, max_turns: int = 10) -> list[ConversationTurn]:
        """Get the most recent conversation turns."""
        return self.history[-max_turns:]

    def format_history_for_prompt(self, max_turns: int = 10) -> str:
        """Format recent history as text for LLM prompts."""
        recent = self.get_recent_history(max_turns)
        lines = []
        for turn in recent:
            role = "Customer" if turn.role == "user" else "Assistant"
            lines.append(f"{role}: {turn.content}")
        return "\n".join(lines)

    @property
    def duration(self) -> float:
        """Total conversation duration in seconds."""
        return time.time() - self.started_at

    @property
    def idle_time(self) -> float:
        """Time since last activity in seconds."""
        return time.time() - self.last_activity


class ConversationManager:
    """
    Manages conversation lifecycle and state transitions.
    
    Handles:
    - State machine transitions
    - Task completion callbacks
    - Timeout handling
    """

    def __init__(
        self,
        language: str = "it",
        idle_timeout: float = 30.0,
        max_duration: float = 600.0,
    ):
        self.language = language
        self.idle_timeout = idle_timeout
        self.max_duration = max_duration
        self.state: ConversationState | None = None
        self._task_callbacks: dict[str, Callable[[AgentTask], None]] = {}

    def start_conversation(self, customer_context: dict[str, Any] | None = None) -> ConversationState:
        """Start a new conversation."""
        self.state = ConversationState(
            language=self.language,
            customer_context=customer_context or {}
        )
        return self.state

    def end_conversation(self) -> None:
        """End the current conversation."""
        if self.state:
            self.state.phase = ConversationPhase.ENDED

    def transition_to(self, phase: ConversationPhase) -> None:
        """Transition to a new conversation phase."""
        if self.state:
            self.state.phase = phase
            self.state.last_activity = time.time()

    def process_user_input(self, text: str) -> None:
        """Process user input and update state."""
        if not self.state:
            raise RuntimeError("No active conversation")
        
        self.state.add_user_turn(text)
        self.transition_to(ConversationPhase.PROCESSING)

    def register_task_callback(
        self,
        task_id: str,
        callback: Callable[[AgentTask], None]
    ) -> None:
        """Register a callback for when a task completes."""
        self._task_callbacks[task_id] = callback

    def on_task_completed(self, task_id: str, result: Any) -> None:
        """Handle task completion."""
        if not self.state:
            return
        
        task = self.state.pending_tasks.get(task_id)
        if task:
            task.mark_completed(result)
            
            # Call registered callback
            callback = self._task_callbacks.pop(task_id, None)
            if callback:
                callback(task)

    def on_task_failed(self, task_id: str, error: str) -> None:
        """Handle task failure."""
        if not self.state:
            return
        
        task = self.state.pending_tasks.get(task_id)
        if task:
            task.mark_failed(error)

    def check_timeouts(self) -> bool:
        """
        Check for conversation timeouts.
        
        Returns:
            True if conversation should end due to timeout.
        """
        if not self.state:
            return False
        
        if self.state.idle_time > self.idle_timeout:
            return True
        
        if self.state.duration > self.max_duration:
            return True
        
        return False

    def get_conversation_summary(self) -> dict[str, Any]:
        """Get a summary of the current conversation state."""
        if not self.state:
            return {"status": "no_active_conversation"}
        
        return {
            "conversation_id": self.state.conversation_id,
            "language": self.state.language,
            "phase": self.state.phase.value,
            "duration_seconds": self.state.duration,
            "turn_count": len(self.state.history),
            "pending_tasks": len(self.state.get_pending_tasks()),
            "customer_context": self.state.customer_context,
        }

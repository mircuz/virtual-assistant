"""
Async Agent Dispatcher

Dispatches agent tasks to run in background threads/processes,
allowing the conversation to continue while waiting for results.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from ..conversation.state_manager import AgentTask, TaskStatus


@dataclass
class DispatchResult:
    """Result of dispatching an agent task."""
    task_id: str
    dispatched: bool
    error: str | None = None


class AgentDispatcher:
    """
    Dispatches agent tasks to run asynchronously.
    
    Uses a thread pool to run agent functions in background,
    calling registered callbacks when tasks complete.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the dispatcher.
        
        Args:
            max_workers: Maximum concurrent agent tasks.
        """
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: dict[str, AgentTask] = {}
        self._callbacks: dict[str, Callable[[AgentTask], None]] = {}
        self._lock = threading.Lock()

    def dispatch(
        self,
        agent_fn: Callable[..., Any],
        args: dict[str, Any],
        agent_name: str,
        action: str,
        callback: Callable[[AgentTask], None] | None = None,
    ) -> DispatchResult:
        """
        Dispatch an agent task to run in the background.
        
        Args:
            agent_fn: The agent function to call.
            args: Arguments to pass to the agent function.
            agent_name: Name of the agent (for logging/tracking).
            action: Action being performed (e.g., "check_availability").
            callback: Optional callback to call when task completes.
        
        Returns:
            DispatchResult with task_id and status.
        """
        task_id = str(uuid4())
        
        task = AgentTask(
            task_id=task_id,
            agent_name=agent_name,
            action=action,
            args=args,
            status=TaskStatus.RUNNING,
        )
        
        with self._lock:
            self._tasks[task_id] = task
            if callback:
                self._callbacks[task_id] = callback
        
        # Submit to thread pool
        future = self._executor.submit(self._execute_task, task, agent_fn, args)
        future.add_done_callback(lambda f: self._on_task_done(task_id, f))
        
        return DispatchResult(task_id=task_id, dispatched=True)

    def _execute_task(
        self,
        task: AgentTask,
        agent_fn: Callable[..., Any],
        args: dict[str, Any],
    ) -> Any:
        """Execute the agent function."""
        try:
            result = agent_fn(**args)
            return result
        except Exception as e:
            raise e

    def _on_task_done(
        self,
        task_id: str,
        future: concurrent.futures.Future,
    ) -> None:
        """Handle task completion."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            
            try:
                result = future.result()
                task.mark_completed(result)
            except Exception as e:
                task.mark_failed(str(e))
            
            # Call registered callback
            callback = self._callbacks.pop(task_id, None)
        
        if callback and task:
            try:
                callback(task)
            except Exception as e:
                print(f"Error in task callback: {e}")

    def get_task(self, task_id: str) -> AgentTask | None:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def get_pending_tasks(self) -> list[AgentTask]:
        """Get all pending/running tasks."""
        with self._lock:
            return [
                t for t in self._tasks.values()
                if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            ]

    def wait_for_task(self, task_id: str, timeout: float = 30.0) -> AgentTask | None:
        """
        Wait for a specific task to complete.
        
        Args:
            task_id: ID of the task to wait for.
            timeout: Maximum time to wait in seconds.
        
        Returns:
            Completed task or None if timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            task = self.get_task(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return task
            time.sleep(0.1)
        return None

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the dispatcher."""
        self._executor.shutdown(wait=wait)


# Global dispatcher instance
_dispatcher: AgentDispatcher | None = None


def get_dispatcher() -> AgentDispatcher:
    """Get or create the global dispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = AgentDispatcher()
    return _dispatcher


def dispatch_agent(
    agent_fn: Callable[..., Any],
    args: dict[str, Any],
    agent_name: str,
    action: str,
    callback: Callable[[AgentTask], None] | None = None,
) -> DispatchResult:
    """
    Convenience function to dispatch an agent task.
    
    Args:
        agent_fn: The agent function to call.
        args: Arguments to pass to the agent function.
        agent_name: Name of the agent.
        action: Action being performed.
        callback: Optional completion callback.
    
    Returns:
        DispatchResult with task_id and status.
    """
    dispatcher = get_dispatcher()
    return dispatcher.dispatch(
        agent_fn=agent_fn,
        args=args,
        agent_name=agent_name,
        action=action,
        callback=callback,
    )


# Async support for environments that use asyncio
async def dispatch_agent_async(
    agent_fn: Callable[..., Any],
    args: dict[str, Any],
    agent_name: str,
    action: str,
) -> AgentTask:
    """
    Async version of dispatch_agent that awaits completion.
    
    Args:
        agent_fn: The agent function to call.
        args: Arguments to pass to the agent function.
        agent_name: Name of the agent.
        action: Action being performed.
    
    Returns:
        Completed AgentTask.
    """
    loop = asyncio.get_event_loop()
    dispatcher = get_dispatcher()
    
    # Create a future to wait on
    future: asyncio.Future[AgentTask] = loop.create_future()
    
    def on_complete(task: AgentTask) -> None:
        loop.call_soon_threadsafe(future.set_result, task)
    
    dispatcher.dispatch(
        agent_fn=agent_fn,
        args=args,
        agent_name=agent_name,
        action=action,
        callback=on_complete,
    )
    
    return await future

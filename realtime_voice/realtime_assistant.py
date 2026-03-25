"""
Real-Time Voice Assistant

Main orchestrator that ties together all components for a natural,
human-like voice conversation experience.

Key features:
- Parallel processing: Listen while extracting intent
- Natural fillers: Use thinking sounds while waiting for agents
- Async agents: Run database queries in background
    - Italian-only conversation flow
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from .conversation.language_config import get_language_config, get_current_language
from .conversation.state_manager import (
    ConversationState,
    ConversationManager,
    ConversationPhase,
    AgentTask,
)
from .conversation.filler_generator import FillerGenerator
from .conversation.response_composer import ResponseComposer
from .agents.dispatcher import AgentDispatcher, dispatch_agent
from .agents.availability_agent import check_availability
from .agents.booking_agent import book_appointment
from .intent_router import IntentRouter
from .voice.streaming_stt import transcribe_audio, get_transcriber
from .voice.tts_manager import TTSManager, get_tts_manager


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


class RealtimeAssistant:
    """
    Real-time voice assistant with natural conversation flow.
    
    Orchestrates:
    - Speech recognition (STT)
    - Intent routing
    - Async agent dispatch
    - Natural filler generation
    - Response composition
    - Speech synthesis (TTS)
    """

    def __init__(
        self,
        predict_fn: Callable[[str, int], str],
        language: str | None = None,
        enable_tts: bool = True,
        mock_tts: bool = False,
    ):
        """
        Initialize the assistant.
        
        Args:
            predict_fn: Function to call LLM (prompt, max_tokens) -> response.
            language: Language code ("it"). Defaults to env config.
            enable_tts: Whether to generate audio responses.
            mock_tts: Use mock TTS for testing.
        """
        self.language = language or get_current_language()
        self.config = get_language_config(self.language)
        
        # Initialize components
        self.conversation_manager = ConversationManager(language=self.language)
        self.filler_generator = FillerGenerator(language=self.language)
        self.response_composer = ResponseComposer(predict_fn, language=self.language)
        self.intent_router = IntentRouter(predict_fn, language=self.language)
        self.agent_dispatcher = AgentDispatcher()
        
        self.predict = predict_fn
        self.enable_tts = enable_tts
        self.tts_manager = get_tts_manager(mock=mock_tts) if enable_tts else None
        
        # Agent function mapping
        self._agent_functions = {
            "check_availability": check_availability,
            "book_appointment": book_appointment,
        }

    def start_conversation(
        self,
        customer_context: dict[str, Any] | None = None,
    ) -> ConversationState:
        """
        Start a new conversation.
        
        Args:
            customer_context: Optional context about the customer.
        
        Returns:
            The new conversation state.
        """
        state = self.conversation_manager.start_conversation(customer_context)
        
        # Generate and speak greeting
        greeting = self.config["greeting"]
        state.add_assistant_turn(greeting)
        
        if self.tts_manager:
            self.tts_manager.speak(greeting, output_filename="greeting.wav")
        
        return state

    def process_turn(
        self,
        audio_path: str | None = None,
        text_input: str | None = None,
        customer_id: str | None = None,
    ) -> TurnResult:
        """
        Process a conversation turn.
        
        This is the main entry point for handling user input.
        
        Args:
            audio_path: Path to audio file (for voice input).
            text_input: Text input (alternative to audio).
            customer_id: Optional customer ID.
        
        Returns:
            TurnResult with all outputs.
        """
        start_time = time.time()
        state = self.conversation_manager.state
        
        if not state:
            state = self.start_conversation(
                customer_context={"customer_id": customer_id} if customer_id else None
            )
        
        # Step 1: Transcribe audio if provided
        if audio_path:
            user_text = transcribe_audio(audio_path, self.language)
        elif text_input:
            user_text = text_input
        else:
            raise ValueError("Either audio_path or text_input must be provided")
        
        # Record user turn
        state.add_user_turn(user_text)
        self.conversation_manager.transition_to(ConversationPhase.PROCESSING)
        
        # Step 2: Route intent (parallel with potential filler)
        routed = self.intent_router.route(user_text, customer_id=customer_id)
        action = routed.get("action")
        args = routed.get("args", {})
        
        # Step 3: Check for missing required fields
        missing = self.intent_router.get_missing_fields(action, args)
        
        if missing:
            # Ask for missing information
            clarification = self.response_composer.compose_clarification_request(
                state, missing
            )
            state.add_assistant_turn(clarification)
            
            audio_path = None
            if self.tts_manager:
                result = self.tts_manager.speak(clarification)
                audio_path = result.audio_path if result.success else None
            
            return TurnResult(
                user_text=user_text,
                response_text=clarification,
                filler_text=None,
                action=action,
                agent_result=None,
                audio_output_path=audio_path,
                processing_time_ms=(time.time() - start_time) * 1000,
            )
        
        # Step 4: Generate filler while dispatching agent
        filler_text = None
        if action in self._agent_functions:
            filler_text = self.filler_generator.generate_for_wait(expected_wait_seconds=2.0)
            
            # Speak filler immediately (non-blocking)
            if self.tts_manager:
                threading.Thread(
                    target=self.tts_manager.speak_filler,
                    args=(filler_text,),
                    daemon=True,
                ).start()
        
        # Step 5: Dispatch agent
        agent_result = None
        if action in self._agent_functions:
            self.conversation_manager.transition_to(ConversationPhase.WAITING_FOR_AGENT)
            
            agent_fn = self._agent_functions[action]
            
            # Filter args to only include valid parameters for the agent
            valid_args = self._filter_agent_args(action, args)
            
            # Execute agent (synchronously for now, but through dispatcher)
            dispatch_result = dispatch_agent(
                agent_fn=agent_fn,
                args=valid_args,
                agent_name=action,
                action=action,
            )
            
            # Wait for result (with timeout)
            task = self.agent_dispatcher.wait_for_task(
                dispatch_result.task_id,
                timeout=30.0,
            )
            
            if task:
                agent_result = task.result
                
                # Create task object for response composer
                agent_task = AgentTask(
                    task_id=task.task_id,
                    agent_name=action,
                    action=action,
                    args=valid_args,
                )
                agent_task.mark_completed(agent_result)
        
        # Step 6: Compose final response
        self.conversation_manager.transition_to(ConversationPhase.RESPONDING)
        
        if action in self._agent_functions and agent_result is not None:
            # Create task for response composer
            task = AgentTask(
                task_id="temp",
                agent_name=action,
                action=action,
                args=args,
            )
            task.mark_completed(agent_result)
            
            response_text = self.response_composer.compose_agent_response(state, task)
        else:
            response_text = self.config["error_message"]
        
        # Record assistant turn
        state.add_assistant_turn(response_text)
        
        # Step 7: Generate TTS for response
        audio_output = None
        if self.tts_manager:
            tts_result = self.tts_manager.speak(response_text)
            audio_output = tts_result.audio_path if tts_result.success else None
        
        self.conversation_manager.transition_to(ConversationPhase.WAITING_FOR_USER)
        
        return TurnResult(
            user_text=user_text,
            response_text=response_text,
            filler_text=filler_text,
            action=action,
            agent_result=agent_result,
            audio_output_path=audio_output,
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    def process_voice_turn(
        self,
        audio_path: str,
        customer_id: str | None = None,
    ) -> TurnResult:
        """
        Process a voice turn (convenience wrapper).
        
        Args:
            audio_path: Path to audio file.
            customer_id: Optional customer ID.
        
        Returns:
            TurnResult with all outputs.
        """
        return self.process_turn(audio_path=audio_path, customer_id=customer_id)

    def process_text_turn(
        self,
        text: str,
        customer_id: str | None = None,
    ) -> TurnResult:
        """
        Process a text turn (convenience wrapper).
        
        Args:
            text: User text input.
            customer_id: Optional customer ID.
        
        Returns:
            TurnResult with all outputs.
        """
        return self.process_turn(text_input=text, customer_id=customer_id)

    def end_conversation(self) -> str:
        """
        End the current conversation.
        
        Returns:
            Farewell message.
        """
        farewell = self.config["farewell"]
        
        if self.conversation_manager.state:
            self.conversation_manager.state.add_assistant_turn(farewell)
        
        self.conversation_manager.end_conversation()
        
        if self.tts_manager:
            self.tts_manager.speak(farewell, output_filename="farewell.wav")
        
        return farewell

    def _filter_agent_args(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Filter args to only include valid parameters for the agent."""
        valid_params = {
            "check_availability": ["service_id", "start_date", "end_date", "staff_id"],
            "book_appointment": ["customer_id", "service_id", "slot_id", "staff_id", "notes"],
        }
        
        allowed = valid_params.get(action, [])
        return {k: v for k, v in args.items() if k in allowed and v is not None}

    def get_conversation_summary(self) -> dict[str, Any]:
        """Get a summary of the current conversation."""
        return self.conversation_manager.get_conversation_summary()


def create_assistant(
    predict_fn: Callable[[str, int], str],
    language: str | None = None,
    enable_tts: bool = True,
) -> RealtimeAssistant:
    """
    Create a real-time assistant.
    
    Args:
        predict_fn: Function to call LLM.
        language: Language code.
        enable_tts: Whether to enable TTS.
    
    Returns:
        Configured RealtimeAssistant.
    """
    return RealtimeAssistant(
        predict_fn=predict_fn,
        language=language,
        enable_tts=enable_tts,
    )

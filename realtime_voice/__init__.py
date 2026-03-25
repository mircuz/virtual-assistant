"""
Real-time Voice Conversation Pipeline

A human-like conversational AI system with:
- Parallel agent processing
- Natural conversation flow with fillers
- Italian-only support
- Async agent orchestration
"""

__version__ = "0.1.0"

from .realtime_assistant import RealtimeAssistant, create_assistant, TurnResult
from .intent_router import IntentRouter, create_router
from .conversation.language_config import (
    get_language_config,
    get_current_language,
    SUPPORTED_LANGUAGES,
)
from .conversation.state_manager import (
    ConversationState,
    ConversationManager,
    ConversationPhase,
)
from .conversation.filler_generator import FillerGenerator, get_filler
from .conversation.response_composer import ResponseComposer
from .agents.dispatcher import AgentDispatcher, dispatch_agent
from .agents.availability_agent import AvailabilityAgent, check_availability
from .agents.booking_agent import BookingAgent, book_appointment
from .voice.streaming_stt import StreamingTranscriber, transcribe_audio
from .voice.tts_manager import TTSManager, get_tts_manager

__all__ = [
    # Main
    "RealtimeAssistant",
    "create_assistant",
    "TurnResult",
    # Router
    "IntentRouter",
    "create_router",
    # Language
    "get_language_config",
    "get_current_language",
    "SUPPORTED_LANGUAGES",
    # Conversation
    "ConversationState",
    "ConversationManager",
    "ConversationPhase",
    "FillerGenerator",
    "get_filler",
    "ResponseComposer",
    # Agents
    "AgentDispatcher",
    "dispatch_agent",
    "AvailabilityAgent",
    "check_availability",
    "BookingAgent",
    "book_appointment",
    # Voice
    "StreamingTranscriber",
    "transcribe_audio",
    "TTSManager",
    "get_tts_manager",
]

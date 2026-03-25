"""
Session management and conversation turn routes for the Virtual Assistant API.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from virtual_assistant.api.models import (
    CreateSessionRequest,
    CreateSessionResponse,
    EndSessionResponse,
    SessionSummaryResponse,
    TurnRequest,
    TurnResponse,
)
from virtual_assistant.core.engine import ConversationEngine, get_engine

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_business_config_dict(req: CreateSessionRequest) -> dict:
    """Convert CreateSessionRequest business config to engine input format."""
    b = req.business
    return {
        "name": b.name,
        "business_type": b.business_type,
        "services": b.services,
        "language": b.language,
        "tone": b.tone,
        "special_instructions": b.special_instructions,
        "agent_capabilities": b.agent_capabilities,
    }


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    engine: Annotated[ConversationEngine, Depends(get_engine)],
) -> CreateSessionResponse:
    """Create a new conversation session from business configuration."""
    business_config = _to_business_config_dict(request)
    result = await engine.create_session(business_config, request.customer_context)
    return CreateSessionResponse(
        session_id=result["session_id"],
        generated_system_prompt=result["generated_system_prompt"],
        greeting=result["greeting"],
        business_name=result["business_name"],
        language=result["language"],
    )


@router.post("/{session_id}/turns", response_model=TurnResponse)
async def process_turn(
    session_id: str,
    request: TurnRequest,
    engine: Annotated[ConversationEngine, Depends(get_engine)],
) -> TurnResponse:
    """Process a conversation turn (text or audio) and return the assistant response."""
    result = await engine.process_turn(
        session_id=session_id,
        text=request.text,
        audio_base64=request.audio_base64,
        customer_id=request.customer_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return TurnResponse(
        session_id=result["session_id"],
        user_text=result["user_text"],
        response_text=result["response_text"],
        filler_text=result.get("filler_text"),
        action=result.get("action"),
        audio_base64=result.get("audio_base64"),
        processing_time_ms=result["processing_time_ms"],
        phase=result["phase"],
    )


@router.get("/{session_id}", response_model=SessionSummaryResponse)
async def get_session(
    session_id: str,
    engine: Annotated[ConversationEngine, Depends(get_engine)],
) -> SessionSummaryResponse:
    """Get summary of an existing session."""
    summary = await engine.get_session_summary(session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionSummaryResponse(
        session_id=summary["session_id"],
        business_name=summary["business_name"],
        phase=summary["phase"],
        duration_seconds=summary["duration_seconds"],
        turn_count=summary["turn_count"],
        language=summary["language"],
    )


@router.delete("/{session_id}", response_model=EndSessionResponse)
async def end_session(
    session_id: str,
    engine: Annotated[ConversationEngine, Depends(get_engine)],
) -> EndSessionResponse:
    """End a session and return farewell with final summary."""
    result = await engine.end_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    summary = result["summary"]
    return EndSessionResponse(
        session_id=result["session_id"],
        farewell=result["farewell"],
        summary=SessionSummaryResponse(
            session_id=summary["session_id"],
            business_name=summary["business_name"],
            phase=summary["phase"],
            duration_seconds=summary["duration_seconds"],
            turn_count=summary["turn_count"],
            language=summary["language"],
        ),
    )

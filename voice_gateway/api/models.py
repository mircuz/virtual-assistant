"""Pydantic models for Voice Gateway API."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class StartConversationRequest(BaseModel):
    shop_id: UUID
    caller_phone: str | None = None


class StartConversationResponse(BaseModel):
    session_id: UUID
    greeting_text: str
    greeting_audio: str | None = None


class TurnRequest(BaseModel):
    text: str | None = None
    audio_base64: str | None = None


class TurnResponse(BaseModel):
    response_text: str
    response_audio: str | None = None
    action_taken: str | None = None


class EndConversationResponse(BaseModel):
    session_id: UUID
    farewell: str

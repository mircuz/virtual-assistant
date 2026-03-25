"""
Pydantic request and response models for the Virtual Assistant API.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class BusinessConfigRequest(BaseModel):
    """Business configuration provided when creating a session."""

    name: str = Field(..., description="Business name")
    business_type: str = Field(
        ...,
        description="Type of business (e.g. hair_salon, restaurant, dental_clinic, general)",
    )
    services: list[str] = Field(default_factory=list, description="List of offered services")
    language: str = Field(default="it", description="Conversation language (ISO 639-1)")
    tone: Literal["friendly", "professional", "formal"] = Field(
        default="friendly",
        description="Communication tone",
    )
    special_instructions: str | None = Field(
        default=None,
        description="Optional extra instructions for the assistant",
    )
    agent_capabilities: list[str] = Field(
        default_factory=lambda: ["check_availability", "book_appointment"],
        description="List of actions the agent can perform",
    )


class CreateSessionRequest(BaseModel):
    """Request body for creating a new conversation session."""

    business: BusinessConfigRequest = Field(..., description="Business configuration")
    customer_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional customer context passed to the engine",
    )


class CreateSessionResponse(BaseModel):
    """Response after successfully creating a session."""

    session_id: str = Field(..., description="Unique session identifier")
    generated_system_prompt: str = Field(
        ...,
        description="System prompt generated from business config",
    )
    greeting: str = Field(..., description="Initial greeting from the assistant")
    business_name: str = Field(..., description="Name of the business")
    language: str = Field(..., description="Session language")


class TurnRequest(BaseModel):
    """Request body for sending a conversation turn."""

    text: str | None = Field(default=None, description="User text input")
    audio_base64: str | None = Field(
        default=None,
        description="Base64-encoded audio (alternative to text)",
    )
    customer_id: str | None = Field(default=None, description="Optional customer identifier")

    @model_validator(mode="after")
    def require_text_or_audio(self) -> "TurnRequest":
        if self.text is None and self.audio_base64 is None:
            raise ValueError("Either text or audio_base64 must be provided")
        return self


class TurnResponse(BaseModel):
    """Response after processing a conversation turn."""

    session_id: str = Field(..., description="Session identifier")
    user_text: str = Field(..., description="Transcribed or provided user text")
    response_text: str = Field(..., description="Assistant response text")
    filler_text: str | None = Field(default=None, description="Optional filler phrase")
    action: str | None = Field(default=None, description="Action taken, if any")
    audio_base64: str | None = Field(default=None, description="Base64-encoded response audio")
    processing_time_ms: float = Field(
        ...,
        description="Time taken to process the turn in milliseconds",
    )
    phase: str = Field(..., description="Current conversation phase")


class SessionSummaryResponse(BaseModel):
    """Summary of an active or ended session."""

    session_id: str = Field(..., description="Session identifier")
    business_name: str = Field(..., description="Business name")
    phase: str = Field(..., description="Current conversation phase")
    duration_seconds: float = Field(..., description="Session duration in seconds")
    turn_count: int = Field(..., description="Number of turns in the session")
    language: str = Field(..., description="Session language")


class EndSessionResponse(BaseModel):
    """Response after ending a session."""

    session_id: str = Field(..., description="Session identifier")
    farewell: str = Field(..., description="Farewell message from the assistant")
    summary: SessionSummaryResponse = Field(
        ...,
        description="Final session summary",
    )

"""Business configuration for the virtual assistant."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class BusinessType(str, Enum):
    HAIR_SALON = "hair_salon"
    RESTAURANT = "restaurant"
    DENTAL_CLINIC = "dental_clinic"
    MEDICAL_CLINIC = "medical_clinic"
    SPA = "spa"
    GYM = "gym"
    GENERAL = "general"

class ToneType(str, Enum):
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    FORMAL = "formal"

@dataclass
class BusinessConfig:
    name: str
    business_type: BusinessType | str = BusinessType.GENERAL
    services: list[str] = field(default_factory=list)
    language: str = "it"
    tone: ToneType | str = ToneType.FRIENDLY
    special_instructions: str | None = None
    agent_capabilities: list[str] = field(default_factory=lambda: ["check_availability", "book_appointment"])

    # Optional metadata
    address: str | None = None
    phone: str | None = None
    opening_hours: str | None = None
